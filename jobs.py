async def send_chunked_reply(message, response_text: str, chunk_size: int = 1900):
    for i in range(0, len(response_text), chunk_size):
        await message.reply(response_text[i:i + chunk_size])
