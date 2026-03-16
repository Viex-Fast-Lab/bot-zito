import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


load_dotenv()

FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY", "").strip()
FIREFLIES_API_URL = os.getenv("FIREFLIES_API_URL", "https://api.fireflies.ai/graphql").strip()


class FirefliesClientError(Exception):
    pass


def is_configured() -> bool:
    return bool(FIREFLIES_API_KEY)


def _headers():
    if not FIREFLIES_API_KEY:
        raise FirefliesClientError("FIREFLIES_API_KEY não configurada.")
    return {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }


def _post_graphql(query: str, variables: dict | None = None):
    response = requests.post(
        FIREFLIES_API_URL,
        headers=_headers(),
        json={"query": query, "variables": variables or {}},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise FirefliesClientError(str(payload["errors"]))
    return payload.get("data", {})


def _normalize_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def list_recent_transcripts(limit: int = 10):
    query = """
    query GetRecentTranscripts($limit: Int!) {
      transcripts(limit: $limit) {
        id
        title
        date
        transcript_url
        duration
        organizer_email
        participants
        summary {
          overview
          bullet_gist
          keywords
          action_items
        }
      }
    }
    """
    data = _post_graphql(query, {"limit": limit})
    return data.get("transcripts", []) or []


def _flatten_action_items(summary: dict | None):
    if not summary:
        return []
    action_items = summary.get("action_items") or []
    normalized = []
    for item in action_items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "text": item.get("text") or item.get("task") or "",
                    "owner": item.get("owner") or item.get("assignee") or "",
                    "due_date": item.get("due_date") or "",
                }
            )
        elif isinstance(item, str):
            normalized.append({"text": item, "owner": "", "due_date": ""})
    return [item for item in normalized if item.get("text")]


def normalize_transcript(raw: dict):
    summary = raw.get("summary") or {}
    return {
        "transcript_id": str(raw.get("id") or ""),
        "source": "fireflies",
        "title": raw.get("title") or "Reunião sem título",
        "date_iso": _normalize_datetime(raw.get("date")),
        "duration_minutes": raw.get("duration"),
        "organizer_email": raw.get("organizer_email") or "",
        "participants": raw.get("participants") or [],
        "summary": {
            "overview": summary.get("overview") or "",
            "bullet_gist": summary.get("bullet_gist") or [],
            "keywords": summary.get("keywords") or [],
        },
        "action_items": _flatten_action_items(summary),
        "transcript_url": raw.get("transcript_url") or "",
        "raw_payload": raw,
    }
