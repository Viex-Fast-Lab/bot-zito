"""
search_github.py — Motor de busca e leitura de Sprints/Tarefas da VIEX via GitHub.

As tarefas da VIEX estão salvas como arquivos Markdown (.md) com cabeçalhos YAML
(frontmatter) nos repositórios 'viex-framework-workflows' e 'viex-viex-gov-001'.

Estrutura típica dos arquivos:
---
title: Nome da Sprint/Tarefa
status: Planejada | Em Andamento | Concluída | Bloqueada | A fazer
supervisores-humanos: Lista de Responsáveis Humanos
papeis-supervisores: [...]
data-inicio: 'YYYY-MM-DD'
data-fim: 'YYYY-MM-DD'
sprint-id: ID
---
"""

import os
import re
import yaml
from github import Github
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Repositórios e pastas onde as sprints/tarefas ficam
SPRINT_SOURCES = [
    {
        "repo": "Viex-Fast-Lab/viex-framework-workflows",
        "path": "docs/framework-de-gestao-colaborativa-de-obras-de-infraestrutura/banco-de-sprints",
    },
    {
        "repo": "Viex-Fast-Lab/viex-viex-gov-001",
        "path": "sprints",
    },
]

def _get_github_client():
    return Github(GITHUB_TOKEN)

def _parse_frontmatter(md_content: str) -> dict:
    """Extrai o bloco YAML de um arquivo Markdown com frontmatter."""
    match = re.match(r"^---\s*\n(.*?)\n---", md_content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}

def _normalize_frontmatter(fm: dict, path: str, repo: str) -> dict:
    """Normaliza os campos do frontmatter para um formato consistente."""
    # Tenta extrair o responsável de vários campos possíveis
    responsavel = fm.get("supervisores-humanos") or fm.get("assignee") or ""
    if isinstance(responsavel, list):
        responsavel = ", ".join([str(r) for r in responsavel if r])
    
    title = fm.get("title", path.split("/")[-1].replace(".md", ""))
    # Remove emojis e caracteres especiais do título para facilitar matching
    title_clean = str(title).encode("ascii", "ignore").decode("ascii").strip()

    return {
        "id": fm.get("sprint-id", path.split("/")[-1].replace(".md", "")),
        "title": str(title),
        "title_ascii": title_clean,
        "status": str(fm.get("status", "?")).strip(),
        "responsavel": str(responsavel).strip() if responsavel else "",
        "data_inicio": str(fm.get("data-inicio", "")),
        "data_fim": str(fm.get("data-fim", "")),
        "path": path,
        "repo": repo,
    }

def list_all_tasks(filtro_responsavel: str = "todas") -> list:
    """
    Lista todas as tarefas/sprints encontradas nos repositórios configurados.
    Usa a API GraphQL do GitHub para buscar todos os arquivos de um diretório em uma única requisição,
    evitando problemas de Rate Limit.
    """
    import base64
    g = _get_github_client()
    resultado = []

    graphql_query = """
    query GetFolderData($owner: String!, $repo: String!, $path: String!) {
      repository(owner: $owner, name: $repo) {
        object(expression: $path) {
          ... on Tree {
            entries {
              name
              object {
                ... on Blob {
                  text
                }
              }
            }
          }
        }
      }
    }
    """

    for source in SPRINT_SOURCES:
        try:
            owner, repo_name = source["repo"].split("/")
            # A expressão para o objeto Tree no GraphQL é "branch:path"
            path_expression = f"HEAD:{source['path']}"
            
            variables = {
                "owner": owner,
                "repo": repo_name,
                "path": path_expression
            }

            # Executa a query GraphQL via o cliente REST do PyGithub
            headers, data = g._Github__requester.requestJsonAndCheck(
                "POST", 
                "https://api.github.com/graphql", 
                input={"query": graphql_query, "variables": variables}
            )

            if "errors" in data:
                print(f"Erro GraphQL ao listar {source['path']}: {data['errors']}")
                continue

            repository_data = data.get("data", {}).get("repository", {})
            if not repository_data or not repository_data.get("object"):
                 continue
                 
            entries = repository_data["object"].get("entries", [])

            for entry in entries:
                if not entry.get("name", "").endswith(".md"):
                    continue
                
                md_text = entry.get("object", {}).get("text", "")
                if not md_text:
                    continue

                try:
                    fm = _parse_frontmatter(md_text)
                    if not fm:
                        continue
                    
                    full_path = f"{source['path']}/{entry['name']}"
                    task = _normalize_frontmatter(fm, full_path, source["repo"])
                    
                    resp = task["responsavel"].lower()
                    filtro = filtro_responsavel.lower().strip()

                    if filtro == "todas":
                        resultado.append(task)
                    elif filtro == "unassigned" and not resp:
                        resultado.append(task)
                    elif filtro not in ("todas", "unassigned") and filtro in resp:
                        resultado.append(task)
                except Exception as e:
                    print(f"Erro ao processar {entry['name']}: {e}")
        except Exception as e:
            print(f"Erro geral ao listar {source['path']} em {source['repo']}: {e}")

    return resultado


def update_task_status(task_path: str, task_repo: str, novo_status: str = None,
                       novo_responsavel: str = None, nova_data_fim: str = None) -> bool:
    """
    Atualiza campos no frontmatter de um arquivo Markdown de Sprint no GitHub.

    Args:
        task_path: Caminho do arquivo no repositório.
        task_repo: Nome completo do repositório (ex: 'Viex-Fast-Lab/viex-viex-gov-001').
        novo_status: Novo valor para o campo 'status'.
        novo_responsavel: Novo valor para o campo 'supervisores-humanos'.
        nova_data_fim: Novo valor para o campo 'data-fim'.
    Returns:
        True em caso de sucesso, False caso contrário.
    """
    g = _get_github_client()
    try:
        repo = g.get_repo(task_repo)
        file_obj = repo.get_contents(task_path)
        md_content = file_obj.decoded_content.decode("utf-8")

        def replace_frontmatter_field(content: str, field: str, new_value: str) -> str:
            pattern = rf"^({re.escape(field)}:\s*)(.+)$"
            replacement = rf"\g<1>{new_value}"
            result = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            # Se o campo não existia, adiciona antes do fechamento do frontmatter
            if result == content:
                result = result.replace("---\n\n", f"{field}: {new_value}\n---\n\n", 1)
            return result

        updated = md_content
        if novo_status:
            updated = replace_frontmatter_field(updated, "status", novo_status)
        if novo_responsavel:
            updated = replace_frontmatter_field(updated, "supervisores-humanos", novo_responsavel)
        if nova_data_fim:
            updated = replace_frontmatter_field(updated, "data-fim", f"'{nova_data_fim}'")

        if updated == md_content:
            return True  # Nada a alterar

        repo.update_file(
            path=task_path,
            message=f"bot(Zito): atualiza tarefa '{task_path.split('/')[-1]}'",
            content=updated.encode("utf-8"),
            sha=file_obj.sha,
        )
        return True
    except Exception as e:
        print(f"Erro ao atualizar {task_path}: {e}")
        return False

def create_new_task(titulo: str, projeto: str, implantacao_de_valor: str, responsavel: str = "", data_fim: str = "", detalhes: str = "") -> str:
    """
    Cria uma nova tarefa do zero como arquivo Markdown no GitHub da VIEX.
    """
    import uuid
    import json
    from datetime import datetime
    
    g = _get_github_client()
    repo_name = "Viex-Fast-Lab/viex-framework-workflows"
    base_path = "docs/framework-de-gestao-colaborativa-de-obras-de-infraestrutura/banco-de-sprints"
    
    task_id = f"ZITO-{str(uuid.uuid4())[:8].upper()}"
    slug = re.sub(r'[^a-zA-Z0-9-]', '-', titulo.lower())
    filename = f"{task_id}-{slug}.md"
    full_path = f"{base_path}/{filename}"
    
    content = f"""---
title: "{titulo}"
status: Planejada
projeto: "{projeto}"
implantacao-de-valor: "{implantacao_de_valor}"
supervisores-humanos: {responsavel}
papeis-supervisores: []
data-inicio: '{datetime.now().strftime('%Y-%m-%d')}'
data-fim: '{data_fim}'
sprint-id: {task_id}
---

{detalhes}"""

    try:
        repo = g.get_repo(repo_name)
        repo.create_file(
            path=full_path,
            message=f"bot(Zito): nova tarefa '{titulo}'",
            content=content.encode("utf-8")
        )
        return json.dumps({"status": "success", "message": f"Tarefa {task_id} criada com sucesso em {full_path}!"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Erro ao criar tarefa: {e}"})
