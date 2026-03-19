import memory_store


def record_discord_message_event(message):
    memory_store.store_discord_message(message, source="live")
    memory_store.update_channel_sync_state(
        channel_id=str(message.channel.id),
        guild_id=str(message.guild.id) if message.guild else "",
        channel_name=getattr(message.channel, "name", ""),
        last_message_id=str(message.id),
        last_message_created_at=message.created_at,
    )
