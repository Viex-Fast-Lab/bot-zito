import os
import requests
import json
from dotenv import load_dotenv

def get_notion_headers():
    load_dotenv()
    token = os.getenv("NOTION_API_KEY")
    if not token:
        raise ValueError("NOTION_API_KEY não encontrada no .env")
    return {
        "Authorization": f"Bearer {token.strip()}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def safe_extract_text(prop_data):
    """Extrai texto seguro de propriedades rich_text ou title do Notion."""
    if not prop_data:
        return ""
    
    text_parts = []
    if isinstance(prop_data, dict):
        # type pode ser 'title' ou 'rich_text'
        prop_type = prop_data.get("type", "")
        items = prop_data.get(prop_type, [])
        for item in items:
            if "plain_text" in item:
                text_parts.append(item["plain_text"])
    elif isinstance(prop_data, list):
         for item in prop_data:
            if "plain_text" in item:
                text_parts.append(item["plain_text"])
    
    return "".join(text_parts).strip()

def safe_extract_people(prop_data):
    """Extrai nomes de propriedades do tipo 'people'."""
    if not prop_data:
        return []
    
    people_names = []
    items = prop_data.get("people", [])
    for person in items:
        if "name" in person:
            people_names.append(person["name"])
    
    return people_names

def safe_extract_select(prop_data):
    """Extrai valor de propriedade do tipo 'select' ou 'status'."""
    if not prop_data:
        return ""
    
    prop_type = prop_data.get("type", "")
    select_data = prop_data.get(prop_type, {})
    if select_data and "name" in select_data:
         return select_data["name"]
    return ""

def fetch_roles(filtro_nome: str = ""):
    """
    Busca do Notion e retorna em uma lista de strings pra leitura do Zito.
    Se filtro_nome for passado, filtra por papéis que contenham aquele nome 
    no Título, Ocupantes Atuais ou Ocupantes Sugeridos.
    """
    database_id = os.getenv("NOTION_DATABASE_ID").strip()
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    try:
        response = requests.post(url, headers=get_notion_headers())
        if response.status_code != 200:
             return f"Erro na API Notion: {response.text}"
             
        data = response.json()
        results = data.get("results", [])
        
        parsed_roles = []
        termo = filtro_nome.lower().strip()
        
        for page in results:
            props = page.get("properties", {})
            title = safe_extract_text(props.get("Papel"))
            ocupantes = safe_extract_people(props.get("Ocupantes"))
            ocupantes_sugeridos = safe_extract_people(props.get("Ocupantes sugeridos"))
            escopo = safe_extract_text(props.get("Escopo"))
            
            # Formata em texto pra IA ler de forma crua
            if title:
                linha = f"Papel: {title}"
                if ocupantes:
                    linha += f" | Ocupantes Atuais: {', '.join(ocupantes)}"
                elif ocupantes_sugeridos:
                    linha += f" | Ocupantes Sugeridos: {', '.join(ocupantes_sugeridos)}"
                else:
                    linha += " | Ocupantes: Nenhum/Vago"
                
                linha += f"\n  Escopo: {escopo}\n"
                
                # Se não tem filtro ou o filtro bater
                if not termo or (termo in linha.lower()):
                    parsed_roles.append(linha)
            
        if not parsed_roles:
            return f"Nenhum papel encontrado para o filtro: '{filtro_nome}'"
            
        return "\n".join(parsed_roles)
            
    except Exception as e:
        return f"Exceção ao ler Notion: {e}"

def create_task_notion(titulo: str, projeto: str, implantacao_de_valor: str, responsavel: str = "", data_fim: str = "", detalhes: str = "") -> str:
    """
    Cria uma nova tarefa (Sprint) diretamente no Banco de Sprints do Notion.
    Mapeia os campos recebidos para as colunas do schema do Notion.
    """
    import uuid
    from datetime import datetime
    
    load_dotenv()
    database_id = os.getenv("NOTION_SPRINTS_DB_ID", "").strip()
    if not database_id:
        return json.dumps({"status": "error", "message": "NOTION_SPRINTS_DB_ID não está configurado. O palhaço esqueceu a tabela!"})
        
    url = "https://api.notion.com/v1/pages"
    task_id = f"ZITO-{str(uuid.uuid4())[:8].upper()}"
    
    # Monta as propriedades conforme o schema visualizado (Banco de Sprints)
    properties = {
        "Sprint": {
            "title": [{"text": {"content": titulo}}]
        },
        "Sprint ID": {
            "rich_text": [{"text": {"content": task_id}}]
        },
        "Status": {
            "status": {"name": "Planejada"} 
        },
        "Supervisores (humanos)": {
            "rich_text": [{"text": {"content": responsavel}}]
        },
        "Data início": {
            "date": {"start": datetime.now().strftime('%Y-%m-%d')}
        }
    }
    
    if data_fim:
         properties["Data fim"] = { "date": {"start": data_fim} }
         
    # Como não tínhamos as colunas projeto/valor_alvo extamente iguais, vamos injetar projeto no valor_alvo e os detalhes/valor no conteúdo da página (block) pra não perder nenhuma info.
    properties["Valor-alvo"] = {
        "rich_text": [{"text": {"content": f"Projeto: {projeto} | Valor: {implantacao_de_valor}"}}]
    }
    
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": detalhes}}]
                }
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=get_notion_headers(), json=payload)
        if response.status_code in [200, 201]:
             page_url = response.json().get("url", "URL desconhecida")
             return json.dumps({"status": "success", "message": f"Tarefa {task_id} criada com sucesso no Notion!\nLink: {page_url}"})
        else:
             return json.dumps({"status": "error", "message": f"Erro {response.status_code} na API do Notion: {response.text}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Exceção ao criar tarefa no Notion: {e}"})

def fetch_daily_notion_updates() -> str:
    """Busca as páginas editadas nas últimas 24 horas no Notion."""
    import datetime
    
    url = "https://api.notion.com/v1/search"
    
    payload = {
        "sort": {
            "direction": "descending",
            "timestamp": "last_edited_time"
        },
        "page_size": 100
    }
    
    try:
        response = requests.post(url, headers=get_notion_headers(), json=payload)
        if response.status_code != 200:
             return f"Erro na API Notion: {response.text}"
             
        data = response.json()
        results = data.get("results", [])
        
        agora = datetime.datetime.now(datetime.timezone.utc)
        limite_24h = agora - datetime.timedelta(hours=24)
        
        atualizacoes = []
        for page in results:
            edited_time_str = page.get("last_edited_time")
            if not edited_time_str:
                continue
            
            # The format is ISO 8601: "2026-03-09T18:05:07.000Z"
            edited_time = datetime.datetime.fromisoformat(edited_time_str.replace("Z", "+00:00"))
            
            created_time_str = page.get("created_time")
            is_new = False
            if created_time_str:
                created_time = datetime.datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
                if created_time >= limite_24h:
                    is_new = True
            
            if edited_time >= limite_24h:
                # extrair titulo
                page_tipo = page.get("object")
                props = page.get("properties", {})
                title = "Página sem título"
                
                # Procura a propriedade do tipo 'title' independente do nome
                for prop_name, prop_data in props.items():
                    if isinstance(prop_data, dict) and prop_data.get("type") == "title":
                        title_arr = prop_data.get("title", [])
                        if title_arr and "plain_text" in title_arr[0]:
                            title = title_arr[0]["plain_text"]
                        break
                
                url_pagina = page.get("url", "")
                
                status_label = "🆕 NOVA PÁGINA" if is_new else "✏️ EDITADA"
                atualizacoes.append(f"- [{status_label}] **{title}** (às {edited_time.strftime('%H:%M')})")
            
        if not atualizacoes:
            return "Nenhuma página foi alterada no Notion nas últimas 24 horas."
            
        return "\n".join(atualizacoes)
            
    except Exception as e:
        return f"Exceção ao ler Notion: {e}"

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    res = fetch_roles("João")
    print(res)
