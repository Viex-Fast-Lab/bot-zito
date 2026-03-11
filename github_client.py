import os
import json
from github import Github
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPO")

if not GITHUB_TOKEN or not REPO_NAME:
    raise ValueError("Missing GITHUB_TOKEN or GITHUB_REPO in environment variables.")

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def get_repo_instance(repo_name: str = None):
    if not repo_name:
        return repo
    if "/" not in repo_name:
        owner = REPO_NAME.split('/')[0]
        return g.get_repo(f"{owner}/{repo_name}")
    return g.get_repo(repo_name)

def get_file_content(filepath: str, repo_name: str = None) -> dict:
    """Reads a JSON file from the GitHub repository."""
    try:
        target_repo = get_repo_instance(repo_name)
        file_content = target_repo.get_contents(filepath)
        decoded_content = file_content.decoded_content.decode('utf-8')
        return json.loads(decoded_content), file_content.sha
    except Exception as e:
        print(f"Error reading {filepath} in {repo_name or REPO_NAME}: {e}")
        return None, None

def update_file_content(filepath: str, data: dict, sha: str, commit_message: str):
    """Updates a JSON file in the GitHub repository."""
    try:
        new_content = json.dumps(data, indent=2, ensure_ascii=False)
        repo.update_file(
            path=filepath,
            message=commit_message,
            content=new_content,
            sha=sha
        )
        return True
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def get_projetos():
    data, _ = get_file_content("Operacional/Kanban/projetos.json")
    return data

def get_iniciativas():
    data, _ = get_file_content("Operacional/Kanban/iniciativas.json")
    return data

def get_organizacao():
    data, _ = get_file_content("Operacional/organizacao.json")
    return data

def list_directory_files(directory_path: str = "", repo_name: str = None) -> list:
    """Retorna uma lista de nomes de arquivos em um diretório do repositório."""
    try:
        target_repo = get_repo_instance(repo_name)
        contents = target_repo.get_contents(directory_path)
        return [f.path for f in contents if f.type == "file"]
    except Exception as e:
        print(f"Error listing {directory_path} in {repo_name or REPO_NAME}: {e}")
        return []

def get_text_file_content(filepath: str, repo_name: str = None) -> str:
    """Lê o conteúdo em texto de um arquivo (Markdown, TXT) para servir de contexto."""
    try:
        target_repo = get_repo_instance(repo_name)
        file_content = target_repo.get_contents(filepath)
        return file_content.decoded_content.decode('utf-8')
    except Exception as e:
        print(f"Error reading text {filepath} in {repo_name or REPO_NAME}: {e}")
        return ""

def create_or_update_text_file(filepath: str, text_content: str, commit_message: str, repo_name: str = None):
    """Cria ou atualiza um arquivo de texto (MD, TXT) no repositório GitHub."""
    target_repo = get_repo_instance(repo_name)
    try:
        # Tenta obter o arquivo para pegar o SHA (se já existir)
        file_content = target_repo.get_contents(filepath)
        target_repo.update_file(
            path=filepath,
            message=commit_message,
            content=text_content,
            sha=file_content.sha
        )
        return True
    except Exception as e:
        # Se não existir, cria o arquivo novo
        try:
            target_repo.create_file(
                path=filepath,
                message=commit_message,
                content=text_content
            )
            return True
        except Exception as create_e:
            print(f"Error creating/updating text file {filepath}: {create_e}")
            return False
