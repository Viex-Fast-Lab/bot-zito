import asyncio
import time
import traceback

import jobs
import routing


def _check_user_cooldown(author_id: int, cooldown_store: dict, cooldown_seconds: int) -> int:
    now_ts = time.time()
    last_message_ts = cooldown_store.get(author_id)
    if last_message_ts is None:
        cooldown_store[author_id] = now_ts
        return 0

    elapsed = now_ts - last_message_ts
    if elapsed < cooldown_seconds:
        return int(cooldown_seconds - elapsed)

    cooldown_store[author_id] = now_ts
    return 0


async def handle_direct_mention(message, bot_user_id: int, cooldown_store: dict, cooldown_seconds: int):
    remaining_cooldown = _check_user_cooldown(message.author.id, cooldown_store, cooldown_seconds)
    if remaining_cooldown > 0:
        await message.reply(
            f"🤡 Ô emocionado! Toma um chazinho e espera mais {remaining_cooldown} segundinhos pra botar a cabeça na lona. Alerta de flood apitando! 🚨"
        )
        return

    clean_prompt = routing.strip_bot_mentions(message, bot_user_id)
    if not clean_prompt:
        await message.reply("O que foi, humano? Me acordou pra quê?")
        return

    async with message.channel.typing():
        try:
            import gemini_logic

            session_id = str(message.channel.id)
            chat_session = gemini_logic.get_chat_session(session_id)
            enriched_prompt = f"[Mensagem de: {message.author.display_name}] {clean_prompt}"

            # Avoid blocking the Discord heartbeat with a sync model call.
            response = await asyncio.to_thread(chat_session.send_message, enriched_prompt)
            response_text = response.text
            await jobs.send_chunked_reply(message, response_text)
        except Exception:
            error_trace = traceback.format_exc()
            print(f"Erro na IA:\n{error_trace}")
            with open("erro_bot.txt", "w", encoding="utf-8") as err_f:
                err_f.write(error_trace)

            if "429 RESOURCE_EXHAUSTED" in error_trace or "429" in error_trace:
                await message.reply(
                    "🤡 Ops! Falei tanto que o Google cortou minha cota (Erro 429 - Limite de requisições). Espera um minutinho e tenta de novo!"
                )
            else:
                await message.reply("Ops! Meu nariz vermelho caiu no servidor e deu um erro interno. Verifique o terminal.")
