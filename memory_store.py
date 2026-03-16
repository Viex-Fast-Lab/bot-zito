import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone


DB_PATH = os.getenv("ZITO_MEMORY_DB", "zito_memory.db")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_get_connection()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                username TEXT,
                is_rafa INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                low_clarity_count INTEGER DEFAULT 0,
                last_seen_at TEXT,
                last_intervention_at TEXT
            );

            CREATE TABLE IF NOT EXISTS discord_messages (
                message_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                channel_name TEXT,
                guild_id TEXT,
                author_id TEXT NOT NULL,
                author_name TEXT,
                username TEXT,
                content TEXT,
                created_at TEXT,
                reference_message_id TEXT,
                mentions_json TEXT,
                attachments_json TEXT,
                is_bot INTEGER DEFAULT 0,
                source TEXT DEFAULT 'live'
            );

            CREATE TABLE IF NOT EXISTS message_analysis (
                message_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                intent TEXT,
                clarity_score INTEGER,
                actionability_score INTEGER,
                needs_intervention INTEGER DEFAULT 0,
                accentuation_issue INTEGER DEFAULT 0,
                team_context_missing INTEGER DEFAULT 0,
                suggested_rewrite TEXT,
                assistant_intervention TEXT,
                profile_signals_json TEXT,
                rationale TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                trigger_message_id TEXT,
                intervention_text TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                channel_id TEXT PRIMARY KEY,
                guild_id TEXT,
                channel_name TEXT,
                last_message_id TEXT,
                last_message_created_at TEXT,
                last_backfill_at TEXT
            );

            CREATE TABLE IF NOT EXISTS meetings (
                transcript_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT,
                date_iso TEXT,
                duration_minutes REAL,
                organizer_email TEXT,
                participants_json TEXT,
                summary_json TEXT,
                action_items_json TEXT,
                transcript_url TEXT,
                raw_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                announced_in_discord INTEGER DEFAULT 0,
                strategic_reviewed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS meeting_sync_state (
                source TEXT PRIMARY KEY,
                last_synced_at TEXT,
                last_meeting_date_iso TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_messages_channel_created
            ON discord_messages(channel_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_messages_author_created
            ON discord_messages(author_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_analysis_user_created
            ON message_analysis(user_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_meetings_date
            ON meetings(date_iso);
            """
        )
        conn.commit()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _normalize_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _json_dump(value):
    return json.dumps(value or [], ensure_ascii=False)


def upsert_user_profile(user_id: str, display_name: str, username: str, is_rafa: bool):
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, display_name, username, is_rafa, message_count, last_seen_at
            ) VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name=excluded.display_name,
                username=excluded.username,
                is_rafa=MAX(user_profiles.is_rafa, excluded.is_rafa),
                last_seen_at=excluded.last_seen_at
            """,
            (user_id, display_name, username, 1 if is_rafa else 0, _utc_now()),
        )
        conn.commit()


def increment_user_message_count(user_id: str):
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            UPDATE user_profiles
            SET message_count = message_count + 1,
                last_seen_at = ?
            WHERE user_id = ?
            """,
            (_utc_now(), user_id),
        )
        conn.commit()


def store_discord_message(message, source: str = "live", is_rafa: bool = False):
    mentions = [getattr(user, "display_name", str(user)) for user in message.mentions]
    attachments = [attachment.url for attachment in getattr(message, "attachments", [])]
    reference_id = None
    if getattr(message, "reference", None) and getattr(message.reference, "message_id", None):
        reference_id = str(message.reference.message_id)

    upsert_user_profile(
        user_id=str(message.author.id),
        display_name=message.author.display_name,
        username=getattr(message.author, "name", message.author.display_name),
        is_rafa=is_rafa,
    )

    with closing(_get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO discord_messages (
                message_id, channel_id, channel_name, guild_id, author_id, author_name,
                username, content, created_at, reference_message_id, mentions_json,
                attachments_json, is_bot, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(message.id),
                str(message.channel.id),
                getattr(message.channel, "name", ""),
                str(message.guild.id) if getattr(message, "guild", None) else "",
                str(message.author.id),
                message.author.display_name,
                getattr(message.author, "name", message.author.display_name),
                message.content or "",
                _normalize_dt(message.created_at),
                reference_id,
                _json_dump(mentions),
                _json_dump(attachments),
                1 if getattr(message.author, "bot", False) else 0,
                source,
            ),
        )
        conn.commit()

    if cursor.rowcount:
        increment_user_message_count(str(message.author.id))


def store_message_analysis(message_id: str, user_id: str, analysis: dict):
    clarity_score = int(analysis.get("clarity_score") or 0)
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO message_analysis (
                message_id, user_id, intent, clarity_score, actionability_score,
                needs_intervention, accentuation_issue, team_context_missing,
                suggested_rewrite, assistant_intervention, profile_signals_json,
                rationale, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                user_id,
                analysis.get("intent", "outro"),
                clarity_score,
                int(analysis.get("actionability_score") or 0),
                1 if analysis.get("needs_intervention") else 0,
                1 if analysis.get("accentuation_issue") else 0,
                1 if analysis.get("team_context_missing") else 0,
                analysis.get("suggested_rewrite", ""),
                analysis.get("assistant_intervention", ""),
                _json_dump(analysis.get("profile_signals") or []),
                analysis.get("rationale", ""),
                _utc_now(),
            ),
        )
        if clarity_score and clarity_score <= 2:
            conn.execute(
                """
                UPDATE user_profiles
                SET low_clarity_count = low_clarity_count + 1
                WHERE user_id = ?
                """,
                (user_id,),
            )
        conn.commit()


def get_recent_channel_context(channel_id: str, limit: int = 12):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT author_name, content, created_at
            FROM discord_messages
            WHERE channel_id = ? AND content != ''
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (channel_id, limit),
        ).fetchall()

    return list(reversed([dict(row) for row in rows]))


def get_recent_discord_messages(days: int = 7, limit: int = 300):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT channel_name, author_name, content, created_at
            FROM discord_messages
            WHERE datetime(created_at) >= datetime('now', ?)
              AND content != ''
              AND is_bot = 0
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_recent_user_analyses(channel_id: str, user_id: str, limit: int = 6):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT a.*, m.channel_id, m.content
            FROM message_analysis a
            JOIN discord_messages m ON m.message_id = a.message_id
            WHERE m.channel_id = ? AND a.user_id = ?
            ORDER BY datetime(a.created_at) DESC
            LIMIT ?
            """,
            (channel_id, user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_last_intervention(channel_id: str, user_id: str):
    with closing(_get_connection()) as conn:
        row = conn.execute(
            """
            SELECT created_at, intervention_text
            FROM interventions
            WHERE channel_id = ? AND user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (channel_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def record_intervention(channel_id: str, user_id: str, trigger_message_id: str, intervention_text: str):
    now = _utc_now()
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO interventions (
                channel_id, user_id, trigger_message_id, intervention_text, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (channel_id, user_id, trigger_message_id, intervention_text, now),
        )
        conn.execute(
            """
            UPDATE user_profiles
            SET last_intervention_at = ?
            WHERE user_id = ?
            """,
            (now, user_id),
        )
        conn.commit()


def get_channel_sync_state(channel_id: str):
    with closing(_get_connection()) as conn:
        row = conn.execute(
            """
            SELECT * FROM sync_state WHERE channel_id = ?
            """,
            (channel_id,),
        ).fetchone()
    return dict(row) if row else None


def update_channel_sync_state(
    channel_id: str,
    guild_id: str,
    channel_name: str,
    last_message_id: str = None,
    last_message_created_at=None,
):
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO sync_state (
                channel_id, guild_id, channel_name, last_message_id,
                last_message_created_at, last_backfill_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                guild_id=excluded.guild_id,
                channel_name=excluded.channel_name,
                last_message_id=COALESCE(excluded.last_message_id, sync_state.last_message_id),
                last_message_created_at=COALESCE(excluded.last_message_created_at, sync_state.last_message_created_at),
                last_backfill_at=excluded.last_backfill_at
            """,
            (
                channel_id,
                guild_id,
                channel_name,
                last_message_id,
                _normalize_dt(last_message_created_at),
                _utc_now(),
            ),
        )
        conn.commit()


def upsert_meeting(
    transcript_id: str,
    source: str,
    title: str,
    date_iso: str,
    duration_minutes,
    organizer_email: str,
    participants,
    summary,
    action_items,
    transcript_url: str,
    raw_payload: dict,
):
    now = _utc_now()
    with closing(_get_connection()) as conn:
        existing = conn.execute(
            "SELECT announced_in_discord, strategic_reviewed FROM meetings WHERE transcript_id = ?",
            (transcript_id,),
        ).fetchone()
        announced = int(existing["announced_in_discord"]) if existing else 0
        reviewed = int(existing["strategic_reviewed"]) if existing else 0
        conn.execute(
            """
            INSERT OR REPLACE INTO meetings (
                transcript_id, source, title, date_iso, duration_minutes, organizer_email,
                participants_json, summary_json, action_items_json, transcript_url, raw_json,
                created_at, updated_at, announced_in_discord, strategic_reviewed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM meetings WHERE transcript_id = ?), ?), ?, ?, ?)
            """,
            (
                transcript_id,
                source,
                title,
                date_iso,
                duration_minutes,
                organizer_email,
                _json_dump(participants),
                json.dumps(summary or {}, ensure_ascii=False),
                _json_dump(action_items),
                transcript_url,
                json.dumps(raw_payload or {}, ensure_ascii=False),
                transcript_id,
                now,
                now,
                announced,
                reviewed,
            ),
        )
        conn.commit()


def get_meeting_sync_state(source: str):
    with closing(_get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM meeting_sync_state WHERE source = ?",
            (source,),
        ).fetchone()
    return dict(row) if row else None


def update_meeting_sync_state(source: str, last_synced_at: str = None, last_meeting_date_iso: str = None):
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO meeting_sync_state (source, last_synced_at, last_meeting_date_iso)
            VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_synced_at = excluded.last_synced_at,
                last_meeting_date_iso = COALESCE(excluded.last_meeting_date_iso, meeting_sync_state.last_meeting_date_iso)
            """,
            (source, last_synced_at or _utc_now(), last_meeting_date_iso),
        )
        conn.commit()


def get_unannounced_meetings(limit: int = 10):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM meetings
            WHERE announced_in_discord = 0
            ORDER BY datetime(date_iso) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_meeting_announced(transcript_id: str):
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            UPDATE meetings
            SET announced_in_discord = 1, updated_at = ?
            WHERE transcript_id = ?
            """,
            (_utc_now(), transcript_id),
        )
        conn.commit()


def get_recent_meetings(days: int = 7, limit: int = 20):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM meetings
            WHERE datetime(date_iso) >= datetime('now', ?)
            ORDER BY datetime(date_iso) DESC
            LIMIT ?
            """,
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_unreviewed_meetings_for_strategy(limit: int = 20):
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM meetings
            WHERE strategic_reviewed = 0
            ORDER BY datetime(date_iso) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_meetings_reviewed(transcript_ids):
    if not transcript_ids:
        return
    with closing(_get_connection()) as conn:
        conn.executemany(
            """
            UPDATE meetings
            SET strategic_reviewed = 1, updated_at = ?
            WHERE transcript_id = ?
            """,
            [(_utc_now(), transcript_id) for transcript_id in transcript_ids],
        )
        conn.commit()
