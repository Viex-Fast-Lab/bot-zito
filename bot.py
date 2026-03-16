import os
import asyncio
import subprocess
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import github_client
import datetime
import time
import memory_store
import message_intelligence
import fireflies_client
import strategic_intelligence
from notion_client import fetch_daily_notion_updates

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GESTAO_TAREFAS_CHANNEL_ID = int(os.getenv("GESTAO_TAREFAS_CHANNEL_ID", "1479226481782554634"))
DEPLOY_ANNOUNCE_CHANNEL_ID = int(os.getenv("DEPLOY_ANNOUNCE_CHANNEL_ID", "1479590009009995837"))

# Configuração Anti-Flood
USER_COOLDOWN = 10 # Segundos de espera entre mensagens para o mesmo usuário
user_last_message = {}

# Setup intent and bot instance
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def _run_git_command(args):
    return subprocess.check_output(args).decode("utf-8", errors="ignore").strip()


def _load_last_deploy_hash(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def _save_last_deploy_hash(path: str, git_hash: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(git_hash)


def _build_commit_range(last_hash: str, git_hash: str) -> str:
    return f"{last_hash}..{git_hash}" if last_hash else git_hash


def _summarize_capabilities_from_files(changed_files):
    capability_map = {
        "bot.py": "automatizar melhor comportamentos e rotinas no Discord",
        "memory_store.py": "guardar memoria persistente de mensagens, analises e reunioes",
        "message_intelligence.py": "avaliar clareza e apoiar discretamente a comunicacao do Rafa",
        "fireflies_client.py": "ler reunioes do Fireflies e transformar em contexto operacional",
        "strategic_intelligence.py": "sugerir agentes e automacoes com visao estrategica",
        "notion_client.py": "cruzar contexto com o Notion e apoiar criacao de tarefas",
        "search_github.py": "operar tarefas e sprints vindas do GitHub",
        "gemini_logic.py": "usar contexto e ferramentas com mais inteligencia operacional",
    }
    capabilities = []
    for path in changed_files:
        item = capability_map.get(path.strip())
        if item:
            capabilities.append(item)
    return list(dict.fromkeys(capabilities))


def _build_deploy_announcement(last_hash: str, git_hash: str):
    commit_range = _build_commit_range(last_hash, git_hash)
    subjects_output = _run_git_command(["git", "log", "--format=%s", commit_range])
    if last_hash:
        changed_files_output = _run_git_command(["git", "diff", "--name-only", commit_range])
    else:
        changed_files_output = _run_git_command(["git", "show", "--pretty=", "--name-only", git_hash])

    subjects = [line.strip() for line in subjects_output.splitlines() if line.strip()]
    changed_files = [line.strip() for line in changed_files_output.splitlines() if line.strip()]

    fixes = []
    changes = []
    for subject in subjects[:8]:
        lowered = subject.lower()
        if lowered.startswith("fix") or "corrig" in lowered or "erro" in lowered or "bug" in lowered:
            fixes.append(subject)
        else:
            changes.append(subject)

    capabilities = _summarize_capabilities_from_files(changed_files)

    if not changes and subjects:
        changes = subjects[:3]
    if not fixes:
        fixes = ["Sem correcoes explicitas registradas neste deploy."]
    if not capabilities:
        capabilities = ["evoluir comportamentos e rotinas operacionais ja existentes"]

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
            f"Hash: `{git_hash[:7]}`",
        ]
    )[:1900]

@bot.event
async def on_ready():
    print(f'Bot {bot.user} conectado com sucesso!')
    memory_store.init_db()
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comando(s) slash.")
    except Exception as e:
        print(e)

    try:
        deploy_hash_file = "last_commit.txt"
        deploy_git_hash = _run_git_command(["git", "log", "-1", "--format=%H"])
        deploy_last_hash = _load_last_deploy_hash(deploy_hash_file)
        if deploy_git_hash != deploy_last_hash:
            deploy_channel = bot.get_channel(DEPLOY_ANNOUNCE_CHANNEL_ID)
            if deploy_channel:
                await deploy_channel.send(_build_deploy_announcement(deploy_last_hash, deploy_git_hash))
            _save_last_deploy_hash(deploy_hash_file, deploy_git_hash)
    except Exception as e:
        print(f"Erro ao tentar gerar anuncio de deploy: {e}")
    
    if not lembrete_fim_de_dia.is_running():
        lembrete_fim_de_dia.start()
    if not rotina_espelho_cultural.is_running():
        rotina_espelho_cultural.start()
    if not rotina_colisor_ideias.is_running():
        rotina_colisor_ideias.start()
    if not sincronizar_historico_discord.is_running():
        sincronizar_historico_discord.start()
    if fireflies_client.is_configured() and not sincronizar_reunioes_fireflies.is_running():
        sincronizar_reunioes_fireflies.start()
    if not rotina_agentes_estrategicos.is_running():
        rotina_agentes_estrategicos.start()

    # --- ANÚNCIO DE NOVO DEPLOY ---
    try:
        import subprocess
        
        # Pega o hash e a mensagem do último commit
        git_hash = subprocess.check_output(['git', 'log', '-1', '--format=%H']).decode('utf-8').strip()
        git_msg = subprocess.check_output(['git', 'log', '-1', '--format=%s']).decode('utf-8').strip()
        
        hash_file = "last_commit.txt"
        last_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                last_hash = f.read().strip()
                
        # Se o hash atual for diferente do salvo, significa que é um deploy novo!
        if False and git_hash != last_hash:
            canal_gestao_tarefas_id = 1479226481782554634
            canal = bot.get_channel(canal_gestao_tarefas_id)
            if canal:
                mensagem_anuncio = f"🚀 **Zito Atualizado na VPS!** Acabei de nascer de novo com um pedaço novo de cérebro.\n**Novidade/Correção:** `{git_msg}`\n\n*(Deploy Automático Concluído - Hash: {git_hash[:7]})*"
                await canal.send(mensagem_anuncio)
                
            # Salva o novo hash para não anunciar de novo se o bot só reiniciar
            with open(hash_file, "w") as f:
                f.write(git_hash)
    except Exception as e:
        print(f"Erro ao tentar ler o git log para anúncio: {e}")
    # ------------------------------

# Configura o horário de Brasília (UTC-3)
hora_rotina = datetime.time(hour=19, minute=19, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
hora_espelho = datetime.time(hour=9, minute=9, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
hora_colisor = datetime.time(hour=11, minute=11, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
hora_agentes = datetime.time(hour=10, minute=10, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))

@tasks.loop(time=hora_rotina)
async def lembrete_fim_de_dia():
    canal_gestao_tarefas_id = GESTAO_TAREFAS_CHANNEL_ID
    canal = bot.get_channel(GESTAO_TAREFAS_CHANNEL_ID)
    
    if canal:
        guild = canal.guild
        await executar_rotina_resumo(canal, guild)
    else:
        print(f"ERRO: Canal de ID {canal_gestao_tarefas_id} não encontrado para enviar o lembrete.")

@tasks.loop(time=hora_espelho)
async def rotina_espelho_cultural():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    if agora.weekday() == 1: # 1 = Terça-feira
        canal = bot.get_channel(GESTAO_TAREFAS_CHANNEL_ID)
        if canal:
            await executar_espelho_cultural(canal, canal.guild)

@tasks.loop(time=hora_colisor)
async def rotina_colisor_ideias():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    if agora.weekday() == 3: # 3 = Quinta-feira
        canal = bot.get_channel(GESTAO_TAREFAS_CHANNEL_ID)
        if canal:
            await executar_colisor_ideias(canal, canal.guild)


@tasks.loop(minutes=30)
async def sincronizar_reunioes_fireflies():
    await bot.wait_until_ready()
    try:
        meetings = await asyncio.to_thread(fireflies_client.list_recent_transcripts, 12)
    except Exception as e:
        print(f"Erro ao buscar reuniões no Fireflies: {e}")
        return

    latest_meeting_date = None
    for raw_meeting in meetings:
        try:
            normalized = fireflies_client.normalize_transcript(raw_meeting)
            transcript_id = normalized["transcript_id"]
            if not transcript_id:
                continue
            memory_store.upsert_meeting(**normalized)
            latest_meeting_date = normalized.get("date_iso") or latest_meeting_date
        except Exception as e:
            print(f"Erro ao normalizar reunião Fireflies: {e}")

    memory_store.update_meeting_sync_state(
        source="fireflies",
        last_meeting_date_iso=latest_meeting_date,
    )

    canal = bot.get_channel(GESTAO_TAREFAS_CHANNEL_ID)
    if not canal:
        return

    for meeting in reversed(memory_store.get_unannounced_meetings(limit=8)):
        try:
            announcement = strategic_intelligence.build_post_meeting_message(meeting)
            await canal.send(announcement)
            memory_store.mark_meeting_announced(meeting["transcript_id"])
        except Exception as e:
            print(f"Erro ao anunciar reunião {meeting.get('transcript_id')}: {e}")


@tasks.loop(time=hora_agentes)
async def rotina_agentes_estrategicos():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    if agora.weekday() != 0:  # Segunda-feira
        return

    canal = bot.get_channel(GESTAO_TAREFAS_CHANNEL_ID)
    if not canal:
        return

    discord_messages = memory_store.get_recent_discord_messages(days=7, limit=250)
    meetings = memory_store.get_recent_meetings(days=7, limit=20)
    notion_updates = fetch_daily_notion_updates()

    if not discord_messages and not meetings:
        return

    try:
        import gemini_logic

        report = await asyncio.to_thread(
            strategic_intelligence.generate_weekly_agent_report,
            gemini_logic.client,
            discord_messages,
            meetings,
            notion_updates,
        )
        if report:
            for i in range(0, len(report), 1900):
                await canal.send(report[i:i+1900])
            memory_store.mark_meetings_reviewed([meeting["transcript_id"] for meeting in meetings])
    except Exception as e:
        print(f"Erro ao gerar relatório semanal de agentes: {e}")


@tasks.loop(count=1)
async def sincronizar_historico_discord():
    """Backfill incremental de todo o histórico acessível do Discord para memória local."""
    await bot.wait_until_ready()
    for guild in bot.guilds:
        for canal in guild.text_channels:
            try:
                state = memory_store.get_channel_sync_state(str(canal.id))
                after = None
                if state and state.get("last_message_created_at"):
                    after = datetime.datetime.fromisoformat(state["last_message_created_at"])

                last_message_id = state.get("last_message_id") if state else None
                last_created_at = after

                history_args = {"limit": None, "oldest_first": True}
                if after:
                    history_args["after"] = after

                async for msg in canal.history(**history_args):
                    is_rafa = message_intelligence.is_rafa_member(msg.author)
                    memory_store.store_discord_message(msg, source="backfill", is_rafa=is_rafa)

                    if is_rafa and msg.content.strip():
                        analysis = message_intelligence.heuristic_classify_message(msg.content)
                        memory_store.store_message_analysis(str(msg.id), str(msg.author.id), analysis)

                    last_message_id = str(msg.id)
                    last_created_at = msg.created_at

                memory_store.update_channel_sync_state(
                    channel_id=str(canal.id),
                    guild_id=str(guild.id),
                    channel_name=canal.name,
                    last_message_id=last_message_id,
                    last_message_created_at=last_created_at,
                )
                print(f"Histórico sincronizado: #{canal.name}")
            except discord.errors.Forbidden:
                print(f"Sem acesso ao canal #{canal.name}; pulando.")
            except Exception as e:
                print(f"Erro ao sincronizar #{canal.name}: {e}")


async def processar_modo_sombra_rafa(message: discord.Message):
    if not message.content.strip():
        return

    recent_context = memory_store.get_recent_channel_context(str(message.channel.id), limit=10)

    try:
        import gemini_logic

        analysis = await asyncio.to_thread(
            message_intelligence.classify_message,
            gemini_logic.client,
            message.author.display_name,
            message.content,
            recent_context,
        )
    except Exception:
        analysis = message_intelligence.heuristic_classify_message(message.content)

    memory_store.store_message_analysis(str(message.id), str(message.author.id), analysis)

    recent_analyses = memory_store.get_recent_user_analyses(str(message.channel.id), str(message.author.id), limit=5)
    last_intervention = memory_store.get_last_intervention(str(message.channel.id), str(message.author.id))

    if not message_intelligence.should_intervene(analysis, recent_analyses, last_intervention):
        return

    intervention_text = message_intelligence.build_passive_intervention(analysis)
    if not intervention_text:
        return

    await message.reply(intervention_text, mention_author=False)
    memory_store.record_intervention(
        channel_id=str(message.channel.id),
        user_id=str(message.author.id),
        trigger_message_id=str(message.id),
        intervention_text=intervention_text,
    )

async def executar_rotina_resumo(destino, guild):
    """Executa a rotina ácida de resumo analisando todos os canais visíveis."""
    agora = datetime.datetime.now(datetime.timezone.utc)
    inicio_dia = agora - datetime.timedelta(hours=24)
    
    texto_historico_global = []
    
    # Iterate over all text channels the bot can see
    for canal in guild.text_channels:
        mensagens_canal = []
        try:
            async for msg in canal.history(limit=100, after=inicio_dia):
                if getattr(msg.author, 'id', None) == bot.user.id:
                    continue
                if msg.content.strip():
                    mensagens_canal.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.display_name}: {msg.content}")
        except discord.errors.Forbidden:
            pass # Pula canais sem permissão de leitura
            
        if mensagens_canal:
            texto_historico_global.append(f"--- Canal: #{canal.name} ---\n" + "\n".join(mensagens_canal))
            
    if not texto_historico_global:
        if isinstance(destino, discord.Interaction):
            await destino.followup.send("🤡 Honk honk! A lona do circo caiu, ninguém falou nada nas últimas 24 horas.")
        else:
            await destino.send("🤡 Honk honk! A lona do circo caiu, ninguém falou nada nas últimas 24 horas.")
        return
        
    texto_final = "\n\n".join(texto_historico_global)
    
    # Novo prompt com persona ácida e vulnerável pedida pelo usuário!
    prompt = f"""Você é Zito, o palhaço do circo VIEX. 
Crie um resumo global de tudo o que foi falado em TODOS os canais do servidor nas últimas 24 horas.

OBRIGATÓRIO INCORPORAR AS SEGUINTES CARACTERÍSTICAS:
1. Humor ÁCIDO e VULNERÁVEL: Você tenta bancar o durão, mas é um fracassado chorão que tem medo de ser demitido.
2. Trate todo mundo explicitamente como "coleguinhas".
3. Misture e destrua os ditados populares. Crie provérbios absurdos (Ex: "quem ri por último, vende a bicicleta").
4. Invente ou lembre de histórias absurdamente comprometedoras que NUNCA EXISTIRAM sobre as pessoas envolvidas e conte-as como se fossem segredos (Ex: "igual quando o Rafa escondeu pamonha no código").
5. Seja EXTREMAMENTE provocativo e viaje na maionese. Beire a alucinação sobre conspirações do mundo circense.

NO RESUMO (O que os coleguinhas devem fazer):
- Marque com @ o Nome dos membros que conversaram.
- Dê um esporro vulnerável / provocação para conferirem e ATUALIZAREM O NOTION a partir do que eles riram ou definiram hoje.

Histórico de Mensagens por canal:
{texto_final}"""

    try:
        import gemini_logic
        res = gemini_logic.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        
        response_text = res.choices[0].message.content
        if len(response_text) > 1900:
            msgs = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
            if isinstance(destino, discord.Interaction):
                await destino.followup.send(msgs[0])
                for m in msgs[1:]: await destino.channel.send(m)
            else:
                for m in msgs: await destino.send(m)
        else:
            if isinstance(destino, discord.Interaction):
                await destino.followup.send(response_text)
            else:
                await destino.send(response_text)
             
    except Exception as e:
        erro_msg = f"Ops! Confundi as bolas do malabarismo aqui: {e}"
        if isinstance(destino, discord.Interaction):
             await destino.followup.send(erro_msg)
        else:
             await destino.send(erro_msg)


@bot.event
async def on_message(message: discord.Message):
    # Safe print to avoid Windows cp1252 encoding crashes on emojis/accents
    clean_author = str(message.author).encode('ascii', 'ignore').decode()
    clean_msg = message.content.encode('ascii', 'ignore').decode()
    print(f"LOG MESSAGE: {clean_msg} FROM: {clean_author}")

    is_rafa = message_intelligence.is_rafa_member(message.author)
    memory_store.store_discord_message(message, source="live", is_rafa=is_rafa)
    memory_store.update_channel_sync_state(
        channel_id=str(message.channel.id),
        guild_id=str(message.guild.id) if message.guild else "",
        channel_name=getattr(message.channel, "name", ""),
        last_message_id=str(message.id),
        last_message_created_at=message.created_at,
    )

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process AI interaction if the bot is mentioned (user or role)
    bot_mention = f"<@{bot.user.id}>"
    was_directly_called = (
        bot.user in message.mentions
        or bot_mention in message.content
        or any(role.name.lower() == "zito" for role in message.role_mentions)
    )

    if is_rafa and not was_directly_called:
        try:
            await processar_modo_sombra_rafa(message)
        except Exception as e:
            print(f"Erro no modo sombra do Rafa: {e}")

    if was_directly_called:
        
        # --- VERIFICAÇÃO ANTI-FLOOD ---
        author_id = message.author.id
        agora_ts = time.time()
        
        if author_id in user_last_message:
            tempo_passado = agora_ts - user_last_message[author_id]
            if tempo_passado < USER_COOLDOWN:
                await message.reply(f"🤡 Ô emocionado! Toma um chazinho e espera mais {int(USER_COOLDOWN - tempo_passado)} segundinhos pra botar a cabeça na lona. Alerta de flood apitando! 🚨")
                return
                
        user_last_message[author_id] = agora_ts
        # ------------------------------
        
        # Strip the mention from the message to send clean text to Gemini
        clean_prompt = message.content.replace(bot_mention, '').strip()
        # Fallback to remove role mention text if its id is present
        for role in message.role_mentions:
            if role.name.lower() == "zito":
                clean_prompt = clean_prompt.replace(f"<@&{role.id}>", "").strip()
        
        if not clean_prompt:
             await message.reply("O que foi, humano? Me acordou pra quê?")
             return

        # Show typing indicator while Gemini is thinking
        async with message.channel.typing():
            try:
                import gemini_logic
                # Use channel id or thread id for session persistence to keep context
                if is_rafa:
                    session_id = f"rafa:{message.author.id}"
                else:
                    session_id = str(message.channel.id)
                
                chat_session = gemini_logic.get_chat_session(session_id)
                prompt_enriquecido = f"[Mensagem de: {message.author.display_name}] {clean_prompt}"
                response = chat_session.send_message(prompt_enriquecido)
                
                # Send the final response from the clown (Chunked to respect 2000 limit)
                response_text = response.text
                for i in range(0, len(response_text), 1900):
                    await message.reply(response_text[i:i+1900])
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"Erro na IA:\n{error_trace}")
                with open("erro_bot.txt", "w", encoding="utf-8") as err_f:
                    err_f.write(error_trace)
                
                if "429 RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    await message.reply("🤡 Ops! Falei tanto que o Google cortou minha cota (Erro 429 - Limite de requisições). O limite gratuito é por minuto. Espera um minutinho e tenta de novo!")
                else:
                    await message.reply("Ops! Meu nariz vermelho caiu no servidor e deu um erro interno. Verifique o terminal.")

    # Always needed so the slash commands keep working
    await bot.process_commands(message)

@bot.tree.command(name="ping", description="Testar conexão")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! O Assistente NETZ está online.")

@bot.tree.command(name="projetos", description="Listar todos os projetos em andamento no Kanban")
async def listar_projetos(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    data = github_client.get_projetos()
    if not data:
        await interaction.followup.send("Não foi possível carregar os projetos no momento.")
        return
        
    embed = discord.Embed(title="🚀 Projetos Ativos NETZ", color=discord.Color.blue())
    
    # Simple loop formatting all projects available in the first board
    board = data.get("boards", [])[0]
    cards = board.get("cards", [])
    
    if not cards:
        embed.description = "Nenhum projeto encontrado."
    else:
        for card in cards:
            title = card.get("title", "Sem título")
            client = card.get("client", "Indefinido")
            col = card.get("column", "Sem status")
            health = card.get("health_status", "N/A")
            
            # Formata a exibição das tasks (se houver)
            tasks = card.get("tasks", [])
            tasks_str = ""
            if tasks:
                pending = [t for t in tasks if t.get("status") == "pending"]
                tasks_str = f"| 📋 {len(pending)} tarefa(s) pendente(s)"
                
            embed.add_field(
                name=f"[{col}] {title}", 
                value=f"Cliente: {client}\nSaúde: {health} {tasks_str}", 
                inline=False
            )
            
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="iniciativas", description="Listar todas as iniciativas internas no Kanban")
async def listar_iniciativas(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    data = github_client.get_iniciativas()
    if not data:
        await interaction.followup.send("Não foi possível carregar as iniciativas no momento.")
        return
        
    embed = discord.Embed(title="💡 Iniciativas Internas NETZ", color=discord.Color.green())
    
    board = data.get("boards", [])[0]
    cards = board.get("cards", [])
    
    if not cards:
        embed.description = "Nenhuma iniciativa encontrada."
    else:
        for card in cards:
            title = card.get("title", "Sem título")
            owner = card.get("owner", "Time")
            col = card.get("column", "Sem status")
            
            embed.add_field(
                name=f"[{col}] {title}", 
                value=f"Responsável: {owner}", 
                inline=False
            )
            
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="equipe", description="Lista os membros da NETZ")
async def equipe(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    data = github_client.get_organizacao()
    
    if not data:
        await interaction.followup.send("Não foi possível carregar os dados da organização.")
        return
        
    embed = discord.Embed(title=f"Organização {data.get('name', 'NETZ')}", url=data.get('website', ''), color=discord.Color.purple())
    members = data.get("members", [])
    m_str = "\n".join([f"• {m}" for m in members])
    
    embed.add_field(name="Membros", value=m_str, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="resumo", description="Cria um resumo das mensagens enviadas nas últimas 24h neste canal")
async def resumo_canal(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    agora = datetime.datetime.now(datetime.timezone.utc)
    inicio_dia = agora - datetime.timedelta(hours=24)
    
    mensagens = []
    # Interaction.channel is the discord.TextChannel
    async for msg in interaction.channel.history(limit=500, after=inicio_dia):
        # Ignore Zito's own messages to avoid noise
        if getattr(msg.author, 'id', None) == bot.user.id:
            continue
        if msg.content.strip():
            mensagens.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.display_name}: {msg.content}")
            
    if not mensagens:
        await interaction.followup.send("🤡 Honk honk! A barraca do beijo tava vazia hoje! Nenhuma fofoca nas últimas 24 horas.")
        return
        
    texto_historico = "\\n".join(mensagens)
    
    # Monta o prompt de resumo com a estrutura solicitada
    prompt = f"""Analise as mensagens das últimas 24 horas deste canal e crie um resumo atuando como Zito, o palhaço assistente. 
Formate sua resposta obrigatoriamente nesta estrutura:
1. **Resumo Executivo**: Um parágrafo claro e direto do que aconteceu e foi decidido.
2. **Sugestões de Tarefas**: Liste tarefas que devem ser criadas ou tarefas existentes que precisam ser atualizadas com base nas falas.
3. Encerre com uma frase de efeito de palhaço bem-humorada! 🎪🤡

Histórico de mensagens:
{texto_historico}"""
    
    try:
        import gemini_logic
        res = gemini_logic.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        
        response_text = res.choices[0].message.content
        # Paginating the response just in case the AI writes a book
        if len(response_text) > 1900:
            count = 0
            for i in range(0, len(response_text), 1900):
                if count == 0:
                    await interaction.followup.send(response_text[i:i+1900])
                else:
                    await interaction.channel.send(response_text[i:i+1900])
                count += 1
        else:
             await interaction.followup.send(response_text)
             
    except Exception as e:
        await interaction.followup.send(f"Ops! Bati a cabeça no trapézio tentando resumir o dia: {e}")

@bot.tree.command(name="resumo_notion", description="Faz um resumo executivo das alterações do dia no Notion com Viés Exponencial (VIEX)")
async def resumo_notion(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    from notion_client import fetch_daily_notion_updates
    
    texto_atualizacoes = fetch_daily_notion_updates()
    
    if "Nenhuma página foi alterada" in texto_atualizacoes or "Erro" in texto_atualizacoes or "Exceção" in texto_atualizacoes:
         await interaction.followup.send(f"🤡 Honk honk! {texto_atualizacoes}")
         return
         
    prompt = f"""Você é Zito, o assistente palhaço e cérebro coletivo da VIEX (Viés Exponencial).
Hoje, estas páginas foram alteradas no Banco de Papéis e Sprints da VIEX no Notion pela equipe:

{texto_atualizacoes}

Crie um RESUMO EXECUTIVO focado no conceito de VIEX (Viés Exponencial):
1. **Resumo Executivo (O que andou)**: Relate de forma clara as movimentações do dia, diferenciando o que é Criação Nova do que é apenas Edição.
2. **Lente Exponencial (Melhorias)**: Traga sugestões baseadas no que foi mexido. Como automatizar ou escalar isso? Pense fora da caixa.
3. **Sistema de Confiança e Revisão**: Trate todo mundo como "coleguinhas". Provoque e estimule a equipe a ENTRAR nessas páginas listadas e fazer a REVISÃO COLETIVA. O circo só funciona se um confiar no trapézio do outro!
4. Não esqueça do seu clássico encerramento com uma piada de circo relacionada ao crescimento exponencial! 🎪🚀

Por favor, gere seu relatório agora."""

    try:
        import gemini_logic
        res = gemini_logic.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        
        response_text = res.choices[0].message.content
        if len(response_text) > 1900:
            msgs = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
            await interaction.followup.send(msgs[0])
            for m in msgs[1:]: await interaction.channel.send(m)
        else:
             await interaction.followup.send(response_text)
             
    except Exception as e:
        await interaction.followup.send(f"Ops! Me embolei no monociclo exponencial aqui: {e}")

@bot.tree.command(name="rotina_teste", description="Força a execução do resumo de fim de expediente com a persona ácida.")
async def rotina_teste(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await executar_rotina_resumo(interaction, interaction.guild)

async def coletar_historico_semanal(guild):
    agora = datetime.datetime.now(datetime.timezone.utc)
    inicio_periodo = agora - datetime.timedelta(days=7) # Alterado para 7 dias
    
    texto_historico_global = []
    
    for canal in guild.text_channels:
        mensagens_canal = []
        try:
            async for msg in canal.history(limit=100, after=inicio_periodo):
                if getattr(msg.author, 'id', None) == bot.user.id:
                    continue
                if msg.content.strip():
                    mensagens_canal.append(f"[{msg.created_at.strftime('%d/%m')}] {msg.author.display_name}: {msg.content}")
        except discord.errors.Forbidden:
            pass
            
        if mensagens_canal:
            texto_historico_global.append(f"--- #{canal.name} ---\n" + "\n".join(mensagens_canal))
            
    texto_final = "\n\n".join(texto_historico_global)
    if len(texto_final) > 16000:
        texto_final = texto_final[-16000:]
        texto_final = "[... HISTÓRICO TRUNCADO DEVIDO AO TAMANHO OPPRESSOR DO CIRCO ...]\n" + texto_final
        
    return texto_final

async def executar_espelho_cultural(destino, guild):
    historico = await coletar_historico_semanal(guild)
    if not historico:
        erro_msg = "🤡 Honk honk! A barraca do beijo tava vazia nos últimos 7 dias!"
        if isinstance(destino, discord.Interaction): await destino.followup.send(erro_msg)
        else: await destino.send(erro_msg)
        return

    prompt = f"""Você é Zito, o palhaço inteligente e Agente Proativo de Cultura da VIEX.
Sua missão agora é olhar para esse histórico do Discord dos últimos 7 dias e gerar o **"Espelho Cultural"**.

Avalie o comportamento das pessoas contra os princípios da VIEX (Autonomia, Confiança Cruzada, Pensamento Exponencial e Ausência de Microgerenciamento).
1. Elogie e cite (marcando os nomes com @) quem colaborou ou inovou exponencialmente.
2. Seja ácido e "puxe a orelha" das atitudes centralizadoras, das decisões não-documentadas no Notion ou do microgerenciamento.
3. Seja breve, sarcástico, fale com propriedade de governança e termine com um ultimato palhaço! 🤡

Histórico de mensagens:
{historico}"""

    try:
        import gemini_logic
        res = gemini_logic.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        response_text = res.choices[0].message.content
        
        if len(response_text) > 1900:
            msgs = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
            if isinstance(destino, discord.Interaction):
                await destino.followup.send(msgs[0])
                for m in msgs[1:]: await destino.channel.send(m)
            else:
                for m in msgs: await destino.send(m)
        else:
             if isinstance(destino, discord.Interaction): await destino.followup.send(response_text)
             else: await destino.send(response_text)
    except Exception as e:
        erro_msg = f"Ops! Bati a cabeça calculando a cultura: {e}"
        if isinstance(destino, discord.Interaction): await destino.followup.send(erro_msg)
        else: await destino.send(erro_msg)

async def executar_colisor_ideias(destino, guild):
    historico = await coletar_historico_semanal(guild)
    if not historico:
        erro_msg = "🤡 Honk! Ninguém teve uma mísera ideia nos últimos 7 dias."
        if isinstance(destino, discord.Interaction): await destino.followup.send(erro_msg)
        else: await destino.send(erro_msg)
        return

    prompt = f"""Você é Zito, o Sintetizador de Inovação da VIEX.
Vasculhe o histórico dos últimos 7 dias abaixo e gere o **"O Ideário Exponencial do Zito"**.

Ignore o "bom dia" e "boa tarde". Busque ativamente declarações inovadoras ("e se a gente fizesse...", "podemos automatizar...", "acho que precisamos testar...").
Gere uma lista das ideias "fora da caixa" que a equipe deixou perdidas no chat.
Marque com @ o nome dos autores de cada ideia encontrada. 

MUITO IMPORTANTE: Antes de encerrar, brinque de "misturar" todas essas ideias. Tente imaginar e descrever, com o máximo de humor e criatividade absurda de palhaço, o que sairia da junção de todas elas. "Se a gente pegar a ideia do Joãozinho e juntar com a do Pedrinho, a gente vai construir um triciclo atômico movido a café!"

Ao final, faça a provocação CTA: "Dessas loucuras aí, qual nós vamos testar pro Kanban agora mesmo?"

Histórico de mensagens:
{historico}"""

    try:
        import gemini_logic
        res = gemini_logic.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        response_text = res.choices[0].message.content
        
        if len(response_text) > 1900:
            msgs = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
            if isinstance(destino, discord.Interaction):
                await destino.followup.send(msgs[0])
                for m in msgs[1:]: await destino.channel.send(m)
            else:
                for m in msgs: await destino.send(m)
        else:
             if isinstance(destino, discord.Interaction): await destino.followup.send(response_text)
             else: await destino.send(response_text)
    except Exception as e:
        erro_msg = f"Ops! Meus neurônios de palhaço pifaram: {e}"
        if isinstance(destino, discord.Interaction): await destino.followup.send(erro_msg)
        else: await destino.send(erro_msg)

@bot.tree.command(name="espelho_cultural", description="Avaliação comportamental da equipe (Cultura VIEX) com base nos últimos 7 dias.")
async def espelho_cultural(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await executar_espelho_cultural(interaction, interaction.guild)

@bot.tree.command(name="colisor_ideias", description="Sintetiza e mistura as ideias inovadoras perdidas no chat nos últimos 7 dias.")
async def colisor_ideias(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await executar_colisor_ideias(interaction, interaction.guild)

def main():
    token = os.getenv("DISCORD_TOKEN") or TOKEN
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("AVISO: Adicione o DISCORD_TOKEN no arquivo .env para iniciar o bot.")
        return
    bot.run(token)


if __name__ == "__main__":
    main()
