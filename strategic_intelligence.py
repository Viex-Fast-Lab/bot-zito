import json


def _safe_load_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return {}


def build_post_meeting_message(meeting: dict) -> str:
    title = meeting.get("title") or "Reunião sem título"
    participants = _safe_load_json(meeting.get("participants_json", "[]"))
    summary = _safe_load_json(meeting.get("summary_json", "{}"))
    action_items = _safe_load_json(meeting.get("action_items_json", "[]"))

    names = ", ".join(participants[:5]) if participants else "coleguinhas"
    overview = (summary.get("overview") or "").strip()
    if not overview:
        overview = "rolou alinhamento importante e o circo aparentemente saiu vivo."

    bullets = summary.get("bullet_gist") or []
    action_lines = []
    for item in action_items[:3]:
        text = (item.get("text") or "").strip()
        if text:
            owner = item.get("owner") or "alguém do time"
            action_lines.append(f"- {text} | Dono sugerido: {owner}")

    parts = [
        f"Pós-reunião VIEX: parabéns, {names}.",
        f"Na reunião **{title}**, o que ficou mais forte foi: {overview}",
    ]
    if action_lines:
        parts.append("Possíveis próximos passos:")
        parts.extend(action_lines)
    parts.append("Isso já deve virar tarefa no Notion ou ficou só como alinhamento?")
    return "\n".join(parts)[:1800]


def generate_weekly_agent_report(ai_client, discord_messages: list, meetings: list, notion_updates_text: str):
    prompt = f"""
Você é o estrategista operacional da VIEX.
Sua missão é sugerir novos agentes e automações de IA com base no contexto da semana.

Princípios:
- Foque em impacto operacional real.
- Não sugira agentes genéricos demais.
- Sugira intervenções discretas, sem deixar o Zito chato.
- Considere Discord, reuniões e movimentações no Notion.
- Faça as sugestões parecerem um experimento vivo de crescimento da VIEX.

Mensagens recentes do Discord:
{json.dumps(discord_messages[-80:], ensure_ascii=False)}

Reuniões recentes:
{json.dumps(meetings[:12], ensure_ascii=False)}

Atualizações recentes do Notion:
{notion_updates_text}

Responda em markdown com:
1. Resumo da semana
2. Sinais estruturais observados
3. Sugestões de novos agentes
4. Sugestões de automações
5. Próximos experimentos
"""
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Você escreve em português claro, estratégico e objetivo.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=1200,
    )
    return (response.choices[0].message.content or "").strip()
