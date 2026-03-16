import json
import os
import re
from datetime import datetime, timedelta, timezone


RAFA_USER_ID = os.getenv("RAFA_DISCORD_USER_ID", "").strip()
RAFA_NAME_HINTS = [
    hint.strip().lower()
    for hint in os.getenv("RAFA_NAME_HINTS", "rafa,rafael").split(",")
    if hint.strip()
]


def is_rafa_member(member) -> bool:
    if RAFA_USER_ID and str(getattr(member, "id", "")) == RAFA_USER_ID:
        return True

    name_candidates = [
        getattr(member, "display_name", ""),
        getattr(member, "name", ""),
        str(member),
    ]
    lowered = " ".join(name_candidates).lower()
    return any(hint in lowered for hint in RAFA_NAME_HINTS)


def _extract_json(content: str):
    content = (content or "").strip()
    if not content:
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _count_accentless_portuguese_tokens(text: str) -> int:
    normalized = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    suspicious = {
        "nao",
        "voce",
        "tambem",
        "ate",
        "ta",
        "to",
        "ja",
        "so",
        "pra",
        "ideia",
    }
    return sum(1 for token in normalized if token in suspicious)


def heuristic_classify_message(text: str) -> dict:
    clean = (text or "").strip()
    lower = clean.lower()
    tokens = re.findall(r"\S+", clean)
    accentless_hits = _count_accentless_portuguese_tokens(clean)
    missing_punctuation = bool(clean) and clean[-1] not in ".?!:"
    has_question = "?" in clean or any(term in lower for term in ["alguem", "pode", "consegue", "sera", "como"])
    has_decision = any(term in lower for term in ["decid", "fechado", "vamos", "combinado"])
    has_idea = any(term in lower for term in ["e se", "poderi", "automat", "teste", "ideia"])
    has_update = any(term in lower for term in ["fiz", "feito", "avancei", "atualizei", "terminei"])

    intent = "outro"
    if has_question:
        intent = "duvida"
    elif has_decision:
        intent = "decisao"
    elif has_idea:
        intent = "ideia"
    elif has_update:
        intent = "atualizacao"

    clarity_score = 4
    reasons = []
    if len(tokens) <= 3:
        clarity_score = 2
        reasons.append("mensagem curta demais para a equipe agir")
    if missing_punctuation:
        clarity_score -= 1
        reasons.append("pontuacao fraca")
    if accentless_hits >= 2:
        clarity_score -= 1
        reasons.append("acentuacao pode atrapalhar a leitura")
    if clean and clean.count(",") + clean.count(".") + clean.count("?") + clean.count("!") == 0 and len(tokens) > 14:
        clarity_score -= 1
        reasons.append("texto corrido")

    clarity_score = max(1, min(5, clarity_score))
    actionability = 3 if any(term in lower for term in ["vamos", "precisa", "falta", "prazo", "hoje"]) else 2
    needs_intervention = clarity_score <= 2
    rewrite = clean

    if needs_intervention and clean:
        rewrite = f"Contexto: {clean}. Proximo passo: alinhar responsavel, prazo e resultado esperado."

    return {
        "intent": intent,
        "clarity_score": clarity_score,
        "actionability_score": actionability,
        "needs_intervention": needs_intervention,
        "accentuation_issue": accentless_hits >= 2 and clarity_score <= 2,
        "team_context_missing": clarity_score <= 2,
        "suggested_rewrite": rewrite,
        "assistant_intervention": (
            f"Vou organizar isso rapidinho para a equipe nao se perder: {rewrite}"
            if needs_intervention and rewrite
            else ""
        ),
        "profile_signals": reasons,
        "rationale": "; ".join(reasons) if reasons else "mensagem suficientemente clara",
    }


def classify_message(ai_client, author_name: str, message_text: str, recent_context: list):
    heuristic = heuristic_classify_message(message_text)

    prompt = f"""
Você é um classificador operacional silencioso da VIEX.
Analise uma mensagem do Rafa e responda APENAS em JSON válido.

Objetivo:
- avaliar se a mensagem está clara para a equipe;
- só sugerir intervenção se houver risco real de interpretação ruim;
- não seja perfeccionista com acentuação: só marque problema se isso atrapalhar o entendimento;
- manter o Zito útil e discreto.

Contexto recente do canal:
{json.dumps(recent_context[-8:], ensure_ascii=False)}

Mensagem do Rafa:
{message_text}

JSON esperado:
{{
  "intent": "pedido|atualizacao|ideia|decisao|duvida|outro",
  "clarity_score": 1,
  "actionability_score": 1,
  "needs_intervention": false,
  "accentuation_issue": false,
  "team_context_missing": false,
  "suggested_rewrite": "reescita curta e mais clara, em portugues",
  "assistant_intervention": "mensagem curtissima que o Zito poderia enviar no canal sem ser chato",
  "profile_signals": ["sinal 1", "sinal 2"],
  "rationale": "uma frase curta"
}}
"""

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você responde apenas JSON válido, sem markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        parsed = _extract_json(response.choices[0].message.content or "")
        if not parsed:
            return heuristic

        parsed.setdefault("intent", heuristic["intent"])
        parsed["clarity_score"] = max(1, min(5, int(parsed.get("clarity_score", heuristic["clarity_score"]))))
        parsed["actionability_score"] = max(1, min(5, int(parsed.get("actionability_score", heuristic["actionability_score"]))))
        parsed["needs_intervention"] = bool(parsed.get("needs_intervention"))
        parsed["accentuation_issue"] = bool(parsed.get("accentuation_issue"))
        parsed["team_context_missing"] = bool(parsed.get("team_context_missing"))
        parsed["profile_signals"] = parsed.get("profile_signals") or heuristic["profile_signals"]
        parsed["suggested_rewrite"] = (parsed.get("suggested_rewrite") or heuristic["suggested_rewrite"]).strip()
        parsed["assistant_intervention"] = (parsed.get("assistant_intervention") or "").strip()
        parsed["rationale"] = (parsed.get("rationale") or heuristic["rationale"]).strip()
        return parsed
    except Exception:
        return heuristic


def should_intervene(analysis: dict, recent_analyses: list, last_intervention: dict):
    if not analysis.get("needs_intervention"):
        return False

    if last_intervention and last_intervention.get("created_at"):
        try:
            last_ts = datetime.fromisoformat(last_intervention["created_at"])
            if datetime.now(timezone.utc) - last_ts < timedelta(minutes=45):
                return False
        except ValueError:
            pass

    unclear_recent = sum(
        1
        for item in recent_analyses
        if int(item.get("clarity_score") or 0) <= 2 or item.get("needs_intervention")
    )
    clarity_score = int(analysis.get("clarity_score") or 5)

    if clarity_score <= 1:
        return True
    if unclear_recent >= 2:
        return True
    return bool(analysis.get("accentuation_issue") and clarity_score <= 2)


def build_passive_intervention(analysis: dict) -> str:
    candidate = (analysis.get("assistant_intervention") or "").strip()
    if candidate:
        return candidate[:350]

    rewrite = (analysis.get("suggested_rewrite") or "").strip()
    if rewrite:
        return f"Vou deixar isso em formato mais claro para o time: {rewrite}"[:350]

    return ""
