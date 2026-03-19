def was_directly_called(message, bot_user_id: int) -> bool:
    bot_mention = f"<@{bot_user_id}>"
    return (
        any(getattr(user, "id", None) == bot_user_id for user in message.mentions)
        or bot_mention in message.content
        or any(role.name.lower() == "zito" for role in message.role_mentions)
    )

def strip_bot_mentions(message, bot_user_id: int) -> str:
    bot_mention = f"<@{bot_user_id}>"
    clean_prompt = message.content.replace(bot_mention, "").strip()
    for role in message.role_mentions:
        if role.name.lower() == "zito":
            clean_prompt = clean_prompt.replace(f"<@&{role.id}>", "").strip()
    return clean_prompt
