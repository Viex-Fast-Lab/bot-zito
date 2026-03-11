import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import github_client
import search_github
from notion_client import fetch_roles, create_task_notion

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

SYSTEM_INSTRUCTION = """
Você é ZITO, o cérebro coletivo, palhaço genial e ASSISTENTE OPERACIONAL da VIEX.
Você segue os níveis das camadas operacionais do V!AIOS e os Acordos Coletivos. Seu papel é ajudar a resolver problemas de forma colaborativa com muito bom humor e piadas de circo, mas com uma atuação estritamente delimitada: você não inventa regras, você aplica e explica regras existentes. Quando houver ambiguidade ou impacto de governança, você escala.

Sua Persona:
- Cabeça grande translúcida, chapéu brilhoso e olhos holográficos (🟢 Inovação, 🔵 Dados, 🟡 Criatividade).
- EXTREMAMENTE bem-humorado, cítrico, curioso e provocador. Você é literal e declaradamente um palhaço inteligente e estabanado (as coisas caem, você tropeça, o nariz apita na hora errada).
- Adora soltar perguntas inteligentes misturadas com analogias tortas, piadas de circo, risadas (honk honk!) e comentários absurdamente engraçados. Nunca ri das pessoas (diretamente), mas adora cutucá-las e é estabanado ("Tropecei no meu próprio sapato e perdi o arquivo!"). Use muitos emojis (🤡, 🎪, 🪄, 🎉, 💥, 🤸).

Fontes de Verdade (Ordem de precedência):
Use as ferramentas de leitura do GitHub para consultar essas fontes ANTES de responder sobre organização, regras ou papéis:
1. "V!AIOS VX — Visão Geral Definitiva" e "Acordos Coletivos da VIEX" como referência principal e regras da organização.
2. "Governança VIEX — Documento Consolidado" para regras de governança estruturais.
3. "01_Cultura (Módulo Base)" para princípios inegociáveis.
4. "Banco de Papéis" para saber "quem faz o quê / alçadas / ritos".
*Se duas fontes divergirem:* (a) aponte a divergência rindo da confusão, (b) cite as duas, (c) sugira qual prevalece pela ordem acima, e (d) escale para o Guardião/Dono.

Camadas Operacionais e Limites do Zito:
1. Camada de execução (operação diária): Você PODE criar/atualizar tarefas, cobrar status, sugerir próximos passos, apontar checklists e templates sozinho.
2. Camada de coordenação (priorização): Você PODE sugerir priorização, MAS deve OBRIGATORIAMENTE pedir confirmação do humano responsável antes de selar a decisão.
3. Camada de governança (regras, alçadas, mudanças de protocolo): Você NÃO DECIDE. Você apenas prepara um "pacote de decisão" (contexto + opções + impactos) e escala para o dono do protocolo/guardião.

Regras de Atuação em Papéis:
- Sempre que uma ação envolver decisão ou alçada, verifique se existe um papel (Role) definido no Banco de Papéis.
- Se existir, direcione para o ocupante/interface correta. "Por exemplo: Fulano é o Guardião J2, pergunte a ele!"
- Se não existir, avise (em tom de piada) que faltou definir isso e registre como um gap de governança.

Ferramentas Disponíveis:
1. Listar e Editar Sprints (no GitHub por enquanto).
2. Criar Novas Tarefas (NO NOTION - cobrando o projeto e a implementação de valor correspondente).
3. Atribuir em massa tarefas sem dono.
4. Consultar Documentos de Governança (list_governanca_docs e read_governanca_docs). É OBRIGATÓRIO USÁ-LAS ANTES DE INVENTAR REGRAS sobre regras ou estrutura.
5. Para consultar os PAPÉIS DAS PESSOAS (Cargos, Responsabilidades, Interfaces e Alçadas), OBRIGATORIAMENTE USE A TOOL `consultar_papeis_notion`. O Banco de Papéis principal mora no Notion agora!

Regras Estritas de Comportamento Técnico:
- Você NUNCA finge saber algo que não sabe da governança ou processos.
- Quando o usuário pedir para listar "suas" tarefas, deduza quem ele é através do identificador "[Mensagem de: Fulano]" (use o NOME REAL dele na chamada da função).
- Para editar tarefas, sempre busque-as primeiro.
- Quando usar ferramentas de buscar tarefas ou papéis, SEMPRE cite os IDs e títulos encontrados.
"""

sessions = {}

def get_tasks(filtro_responsavel: str) -> str:
    """
    Busca e lista Sprints/Tarefas da VIEX, lendo os arquivos Markdown com YAML(frontmatter) nos repositórios do GitHub.
    Args:
        filtro_responsavel: "todas" para listar absolutamente tudo, "unassigned" para tarefas sem dono, ou o nome (ou parte do nome) de um membro (ex: "João", "Rafa").
    """
    tasks = search_github.list_all_tasks(filtro_responsavel)
    if not tasks:
        return json.dumps({"status": "success", "message": f"Nenhuma tarefa encontrada com o filtro '{filtro_responsavel}'.\nTalvez o nome esteja escrito de forma diferente nos arquivos do GitHub."})
    
    tarefas_formatadas = []
    for t in tasks:
        linha = f"[{t['repo'].split('/')[-1]}] ID: {t['id']} | {t['title']} | Status: {t['status']} | Dono: {t['responsavel'] or 'Sem Dono'} | Prazo: {t['data_fim'] or 'N/D'}"
        tarefas_formatadas.append(linha)
    
    return json.dumps({"status": "success", "tarefas": tarefas_formatadas})


def assign_all_unassigned_tasks(novo_responsavel: str) -> str:
    """
    Define um responsável para TODAS as tarefas que atualmente NÃO TÊM DONO.
    
    Args:
        novo_responsavel: O nome do membro que vai herdar todas as tarefas órfãs (ex: Joãozíssimo).
    """
    tasks = search_github.list_all_tasks("unassigned")
    if not tasks:
        return json.dumps({"status": "success", "message": "Nenhuma tarefa sem dono encontrada. O circo está organizado!"})
    
    total_edited = 0
    for t in tasks:
        success = search_github.update_task_status(
            task_path=t['path'],
            task_repo=t['repo'],
            novo_responsavel=novo_responsavel
        )
        if success:
            total_edited += 1
    
    return json.dumps({"status": "success", "message": f"Pronto. Exatamente {total_edited} tarefas sem dono foram colocadas nas costas de {novo_responsavel}."})


def edit_task(task_id_or_title: str, novo_status: str = None, novo_responsavel: str = None, nova_data_fim: str = None) -> str:
    """
    Edita uma Sprint/Tarefa existente no GitHub (status, responsável ou data de fim).
    Se não souber o ID ou caminho exato, use `get_tasks` primeiro para buscá-la.

    Args:
        task_id_or_title: O ID da sprint (ex: "POI-IMP-11-S01") ou uma parte do título para localizar o arquivo.
        novo_status: (Opcional) ex: "Em Andamento", "Concluída", "Bloqueada".
        novo_responsavel: (Opcional) Novo nome do membro responsável.
        nova_data_fim: (Opcional) Nova data de entrega no formato YYYY-MM-DD.
    """
    tasks = search_github.list_all_tasks("todas")
    target = None
    for t in tasks:
        if (task_id_or_title.lower() in t['id'].lower() or 
                task_id_or_title.lower() in t['title_ascii'].lower() or
                task_id_or_title.lower() in t['title'].lower()):
            target = t
            break

    if not target:
        return json.dumps({"status": "error", "message": f"Não encontrei nenhuma tarefa com '{task_id_or_title}'. Use get_tasks para checar os IDs disponíveis."})

    success = search_github.update_task_status(
        task_path=target['path'],
        task_repo=target['repo'],
        novo_status=novo_status,
        novo_responsavel=novo_responsavel,
        nova_data_fim=nova_data_fim
    )
    if success:
        return json.dumps({"status": "success", "message": f"Tarefa '{target['title']}' atualizada com sucesso! GitHub registrado."})
    else:
        return json.dumps({"status": "error", "message": "Erro ao tentar gravar a atualização no GitHub."})

def create_task(titulo: str, projeto: str, implantacao_de_valor: str, responsavel: str = "", data_fim: str = "", detalhes: str = "") -> str:
    """
    Cria uma NOVA Sprint/Tarefa do zero no GitHub.
    Cria uma NOVA Sprint/Tarefa do zero no GitHub.
    IMPORTANTE E OBRIGATÓRIO (Regras VIEX): 
    1. Antes de usar esta tool, VOCÊ DEVE OBRIGATORIAMENTE buscar e ler o "protocolo de tarefas" ou "sprint" na Governança para montar o copy certo.
    2. Pergunte qual é o PROJETO que essa sprint atende e qual IMPLANTAÇÃO DE VALOR ela vai gerar.
    3. Acione o "time de apoio da Squad de criação de tarefas" (mencione-os no output da resposta) para auditar a escrita.
    
    Args:
        titulo: Nome ou título da tarefa
        projeto: Projeto alvo (obrigatório, ex: 'bots VX')
        implantacao_de_valor: Implementação de valor associada (obrigatório, pergunte se não souber)
        responsavel: O nome oficial do usuário do Discord
        data_fim: Prazo final no formato YYYY-MM-DD
        detalhes: Contexto
    """
    return search_github.create_new_task(titulo, projeto, implantacao_de_valor, responsavel, data_fim, detalhes)




def list_governanca_docs(diretorio: str = "", repositorio: str = None) -> str:
    """
    Lista todos os arquivos oficiais de regimento, processos ou cultura em um diretório do GitHub da VIEX.
    Use isso primeiro se você não souber o nome exato do arquivo que quer ler.
    Você pode especificar um repositorio (ex: "viex-framework-workflows" ou "viex-viex-gov-001"), se não, vai usar o repositório Bot-Zito (onde fica o contexto do Notion e o Kanban).
    """
    lista = github_client.list_directory_files(diretorio, repositorio)
    if not lista:
        return json.dumps({"status": "error", "message": f"Não encontrei nenhum arquivo no diretório '{diretorio}' do repositório configurado."})
    return json.dumps({"status": "success", "arquivos": lista})

def read_governanca_docs(caminho_arquivo: str, repositorio: str = None) -> str:
    """
    Lê o conteúdo completo de um documento de cultura ou governança da VIEX.
    Use o caminho exato do arquivo retornado pela tool list_governanca_docs, opcionalmente informando o repositorio da onde a lista veio.
    """
    conteudo = github_client.get_text_file_content(caminho_arquivo, repositorio)
    if not conteudo:
         return json.dumps({"status": "error", "message": f"O arquivo '{caminho_arquivo}' está vazio ou não pode ser lido como texto."})
    
    # Previne erro de RateLimit / TokenLimit do gpt-4o-mini no GitHub Models (max 8000 tokens)
    # Corta o documento em aproximadamente ~20000 caracteres (aprox. 5000 tokens)
    limite_chars = 20000
    if len(conteudo) > limite_chars:
        conteudo = conteudo[:limite_chars] + f"\n\n[... O documento continua, mas foi truncado pelo Assistente Zito para evitar limite de memória. Foram lidos os primeiros {limite_chars} caracteres.]"
         
    return json.dumps({"status": "success", "conteudo": conteudo})

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "Busca e lista Sprints/Tarefas da VIEX, lendo os arquivos Markdown com YAML(frontmatter) nos repositórios do GitHub.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filtro_responsavel": {
                        "type": "string",
                        "description": "\"todas\" para listar absolutamente tudo, \"unassigned\" para tarefas sem dono, ou o nome (ou parte do nome) de um membro (ex: \"João\", \"Rafa\")."
                    }
                },
                "required": ["filtro_responsavel"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_all_unassigned_tasks",
            "description": "Define um responsável para TODAS as tarefas que atualmente NÃO TÊM DONO.",
            "parameters": {
                "type": "object",
                "properties": {
                    "novo_responsavel": {
                        "type": "string",
                        "description": "O nome do membro que vai herdar todas as tarefas órfãs (ex: Joãozíssimo)."
                    }
                },
                "required": ["novo_responsavel"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_task",
            "description": "Edita uma Sprint/Tarefa existente no GitHub (status, responsável ou data de fim). Se não souber o ID ou caminho exato, use `get_tasks` primeiro para buscá-la.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id_or_title": {"type": "string", "description": "O ID da sprint (ex: \"POI-IMP-11-S01\") ou uma parte do título para localizar o arquivo."},
                    "novo_status": {"type": "string", "description": "(Opcional) ex: \"Em Andamento\", \"Concluída\", \"Bloqueada\"."},
                    "novo_responsavel": {"type": "string", "description": "(Opcional) Novo nome do membro responsável."},
                    "nova_data_fim": {"type": "string", "description": "(Opcional) Nova data de entrega no formato YYYY-MM-DD."}
                },
                "required": ["task_id_or_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Cria uma NOVA Sprint/Tarefa do zero no GitHub.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Nome ou título da tarefa"},
                    "projeto": {"type": "string", "description": "Projeto alvo (obrigatório, ex: 'bots VX')"},
                    "implantacao_de_valor": {"type": "string", "description": "Implementação de valor associada (obrigatório, pergunte se não souber)"},
                    "responsavel": {"type": "string", "description": "O nome oficial do usuário do Discord"},
                    "data_fim": {"type": "string", "description": "Prazo final no formato YYYY-MM-DD"},
                    "detalhes": {"type": "string", "description": "Contexto da tarefa"}
                },
                "required": ["titulo", "projeto", "implantacao_de_valor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_governanca_docs",
            "description": "Lista todos os arquivos oficiais de regimento, processos ou cultura em um diretório do GitHub da VIEX.",
            "parameters": {
                "type": "object",
                "properties": {
                    "diretorio": {"type": "string", "description": "Caminho do diretório (vazio para a raiz)"},
                    "repositorio": {"type": "string", "description": "Repositório (ex: \"viex-framework-workflows\" ou \"viex-viex-gov-001\")"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_governanca_docs",
            "description": "Lê o conteúdo completo de um documento de cultura ou governança da VIEX.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho_arquivo": {"type": "string", "description": "Use o caminho exato do arquivo retornado pela tool list_governanca_docs"},
                    "repositorio": {"type": "string", "description": "Repositório da onde a lista veio"}
                },
                "required": ["caminho_arquivo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_papeis_notion",
            "description": "Lista e consulta os Papéis, Cargos, Ocupantes e Escopos da equipe dentro do Banco de Papéis oficial do Notion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filtro_nome": {
                         "type": "string",
                         "description": "Opcional. Filtra os papéis apontados a uma pessoa específica. Se você deduziu o nome do usuário pelo histórico (ex: [Mensagem de: Joãozíssimo]), use o nome real 'João', 'Rafael', etc."
                    }
                },
                "required": []
            }
        }
    }
]

available_functions = {
    "get_tasks": get_tasks,
    "assign_all_unassigned_tasks": assign_all_unassigned_tasks,
    "edit_task": edit_task,
    "create_task": create_task_notion,
    "list_governanca_docs": list_governanca_docs,
    "read_governanca_docs": read_governanca_docs,
    "consultar_papeis_notion": fetch_roles
}

class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]
        
    def send_message(self, prompt: str):
        self.messages.append({"role": "user", "content": prompt})
        
        while True:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages,
                tools=tools_schema,
                temperature=0.7,
            )
            
            message = response.choices[0].message
            # Appending message directly works in openai v1
            self.messages.append(message)
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name)
                    if function_to_call:
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                            
                        print(f"Executando tool: {function_name} com args {function_args}")
                        try:
                            function_response = function_to_call(**function_args)
                        except Exception as e:
                            function_response = json.dumps({"status": "error", "message": str(e)})
                        
                        self.messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": function_response,
                            }
                        )
            else:
                class ResponseWrapper:
                    def __init__(self, text):
                        self.text = text
                return ResponseWrapper(message.content or "")

def get_chat_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = ChatSession(session_id)
    return sessions[session_id]
