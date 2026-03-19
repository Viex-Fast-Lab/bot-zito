import json
import os
import subprocess


def run_git_command(args):
    return subprocess.check_output(args).decode("utf-8", errors="ignore").strip()


async def resolve_channel(bot, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


def load_last_deploy_hash(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_last_deploy_hash(path: str, git_hash: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(git_hash)


def build_commit_range(last_hash: str, git_hash: str) -> str:
    return f"{last_hash}..{git_hash}" if last_hash else git_hash


def load_release_manifest():
    manifest_path = "release_manifest.json"
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_deploy_metadata():
    manifest = load_release_manifest()
    manifest_sha = (manifest.get("sha") or "").strip()
    commit_sha = (
        os.getenv("DEPLOY_COMMIT_SHA")
        or os.getenv("EASYPANEL_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or manifest_sha
        or ""
    ).strip()
    commit_subject = (
        os.getenv("DEPLOY_COMMIT_SUBJECT")
        or os.getenv("EASYPANEL_GIT_COMMIT_MESSAGE")
        or os.getenv("RAILWAY_GIT_COMMIT_MESSAGE")
        or manifest.get("subject", "")
        or ""
    ).strip()
    changed_files_env = (
        os.getenv("DEPLOY_CHANGED_FILES")
        or os.getenv("EASYPANEL_GIT_CHANGED_FILES")
        or ""
    ).strip()

    if changed_files_env:
        changed_files = [item.strip() for item in changed_files_env.split(",") if item.strip()]
    else:
        changed_files = []

    use_manifest_details = bool(manifest) and (
        not commit_sha
        or commit_sha == manifest_sha
        or (manifest.get("subject") or "").strip() == commit_subject
    )
    manifest_changes = manifest.get("changes") or []
    manifest_fixes = manifest.get("fixes") or []
    manifest_capabilities = manifest.get("capabilities") or []

    if commit_sha:
        return {
            "sha": commit_sha,
            "subject": commit_subject,
            "changed_files": changed_files,
            "changes": manifest_changes if use_manifest_details else [],
            "fixes": manifest_fixes if use_manifest_details else [],
            "capabilities": manifest_capabilities if use_manifest_details else [],
            "source": "env",
        }

    if os.path.isdir(".git"):
        sha = run_git_command(["git", "log", "-1", "--format=%H"])
        subject = run_git_command(["git", "log", "-1", "--format=%s"])
        return {
            "sha": sha,
            "subject": subject,
            "changed_files": [],
            "changes": [],
            "fixes": [],
            "capabilities": [],
            "source": "git",
        }

    return {
        "sha": "",
        "subject": "",
        "changed_files": [],
        "changes": manifest_changes,
        "fixes": manifest_fixes,
        "capabilities": manifest_capabilities,
        "source": "unknown",
    }


def summarize_capabilities_from_files(changed_files):
    capability_map = {
        "bot.py": "automatizar melhor comportamentos e rotinas no Discord",
        "memory_store.py": "guardar memoria persistente de mensagens, analises e reunioes",
        "fireflies_client.py": "ler reunioes do Fireflies e transformar em contexto operacional",
        "strategic_intelligence.py": "sugerir agentes e automacoes com visao estrategica",
        "notion_client.py": "cruzar contexto com o Notion e apoiar criacao de tarefas",
        "search_github.py": "operar tarefas e sprints vindas do GitHub",
        "gemini_logic.py": "usar contexto e ferramentas com mais inteligencia operacional",
        "event_ingestion.py": "registrar eventos de Discord de forma mais organizada",
        "routing.py": "rotear mensagens e gatilhos com menos acoplamento",
        "jobs.py": "executar respostas e jobs reutilizaveis com menos duplicacao",
        "runtime.py": "gerenciar deploy e resolucao de canais com mais estabilidade",
    }
    capabilities = []
    for path in changed_files:
        item = capability_map.get(path.strip())
        if item:
            capabilities.append(item)
    return list(dict.fromkeys(capabilities))


def build_deploy_announcement(last_hash: str, git_hash: str):
    subjects = []
    changed_files = []

    metadata = get_deploy_metadata()
    changes = metadata.get("changes") or []
    fixes = metadata.get("fixes") or []
    capabilities = metadata.get("capabilities") or []
    if metadata["source"] == "git" and git_hash:
        commit_range = build_commit_range(last_hash, git_hash)
        subjects_output = run_git_command(["git", "log", "--format=%s", commit_range])
        if last_hash:
            changed_files_output = run_git_command(["git", "diff", "--name-only", commit_range])
        else:
            changed_files_output = run_git_command(["git", "show", "--pretty=", "--name-only", git_hash])
        subjects = [line.strip() for line in subjects_output.splitlines() if line.strip()]
        changed_files = [line.strip() for line in changed_files_output.splitlines() if line.strip()]
    else:
        if metadata.get("subject"):
            subjects = [metadata["subject"]]
        changed_files = metadata.get("changed_files") or []

    if not changes or not fixes:
        derived_changes = []
        derived_fixes = []
        for subject in subjects[:8]:
            lowered = subject.lower()
            if lowered.startswith("fix") or "corrig" in lowered or "erro" in lowered or "bug" in lowered:
                derived_fixes.append(subject)
            else:
                derived_changes.append(subject)
        if not changes:
            changes = derived_changes
        if not fixes:
            fixes = derived_fixes

    if not capabilities:
        capabilities = summarize_capabilities_from_files(changed_files)

    if not changes and subjects:
        changes = subjects[:3]
    if not changes:
        changes = ["Nova versao publicada na VPS com atualizacoes internas do Zito."]
    if not fixes:
        fixes = ["Sem correcoes explicitas registradas neste deploy."]
    if not capabilities:
        capabilities = [
            "evoluir comportamentos e rotinas operacionais ja existentes",
            "rodar rotinas automaticas e memoria operacional com mais estabilidade",
        ]

    return "\n".join(
        [
            "Deploy do Zito concluido.",
            "",
            "**O que mudou**",
            *[f"- {item}" for item in changes[:4]],
            "",
            "**Erros corrigidos**",
            *[f"- {item}" for item in fixes[:4]],
            "",
            "**Agora estou apto a fazer melhor**",
            *[f"- {item}" for item in capabilities[:5]],
            "",
            f"Hash: `{(git_hash or metadata.get('sha') or 'desconhecido')[:7]}`",
        ]
    )[:1900]


async def announce_new_deploy(bot, announce_channel_id: int, hash_file: str = "last_commit.txt"):
    deploy_metadata = get_deploy_metadata()
    deploy_git_hash = deploy_metadata.get("sha") or "runtime"
    deploy_last_hash = load_last_deploy_hash(hash_file)
    if deploy_git_hash == deploy_last_hash:
        return

    deploy_channel = await resolve_channel(bot, announce_channel_id)
    if deploy_channel:
        await deploy_channel.send(build_deploy_announcement(deploy_last_hash, deploy_git_hash))
    save_last_deploy_hash(hash_file, deploy_git_hash)
