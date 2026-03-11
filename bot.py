import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import github_client
import datetime
import time

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração Anti-Flood
USER_COOLDOWN = 10 # Segundos de espera entre mensagens para o mesmo usuário
user_last_message = {}

# Setup intent and bot instance
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} conectado com sucesso!')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizado {len(synced)} comando(s) slash.")
    except Exception as e:
        print(e)
    
    if not lembrete_fim_de_dia.is_running():
        lembrete_fim_de_dia.start()
    if not rotina_espelho_cultural.is_running():
        rotina_espelho_cultural.start()
    if not rotina_colisor_ideias.is_running():
        rotina_colisor_ideias.start()

# Configura o horário de Brasília (UTC-3)
hora_rotina = datetime.time(hour=19, minute=19, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
hora_espelho = datetime.time(hour=9, minute=9, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
hora_colisor = datetime.time(hour=11, minute=11, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))

@tasks.loop(time=hora_rotina)
async def lembrete_fim_de_dia():
    canal_gestao_tarefas_id = 1479226481782554634
    canal = bot.get_channel(canal_gestao_tarefas_id)
    
    if canal:
        guild = canal.guild
        await executar_rotina_resumo(canal, guild)
    else:
        print(f"ERRO: Canal de ID {canal_gestao_tarefas_id} não encontrado para enviar o lembrete.")

@tasks.loop(time=hora_espelho)
async def rotina_espelho_cultural():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    if agora.weekday() == 1: # 1 = Terça-feira
        canal_gestao_tarefas_id = 1479226481782554634
        canal = bot.get_channel(canal_gestao_tarefas_id)
        if canal:
            await executar_espelho_cultural(canal, canal.guild)

@tasks.loop(time=hora_colisor)
async def rotina_colisor_ideias():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    if agora.weekday() == 3: # 3 = Quinta-feira
        canal_gestao_tarefas_id = 1479226481782554634
        canal = bot.get_channel(canal_gestao_tarefas_id)
        if canal:
            await executar_colisor_ideias(canal, canal.guild)

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
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process AI interaction if the bot is mentioned (user or role)
    bot_mention = f"<@{bot.user.id}>"
    if bot.user in message.mentions or bot_mention in message.content or any(role.name.lower() == "zito" for role in message.role_mentions):
        
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

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("AVISO: Adicione o DISCORD_TOKEN no arquivo .env para iniciar o bot.")
    else:
        bot.run(TOKEN)
