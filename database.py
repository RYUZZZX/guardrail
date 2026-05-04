import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "usage.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calls (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            INTEGER NOT NULL,
            provider      TEXT    NOT NULL,
            model         TEXT    NOT NULL,
            job_id        TEXT,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd      REAL    DEFAULT 0,
            duration_ms   INTEGER DEFAULT 0,
            status        TEXT    DEFAULT 'ok'
        );

        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        INSERT OR IGNORE INTO config (key, value) VALUES ('monthly_budget_usd', '500');
        INSERT OR IGNORE INTO config (key, value) VALUES ('pause_at_pct',       '75');
        INSERT OR IGNORE INTO config (key, value) VALUES ('kill_at_pct',        '95');
        INSERT OR IGNORE INTO config (key, value) VALUES ('per_job_token_limit','500000');
    """)
    conn.commit()
    conn.close()
    print("[db] ready")


def record_call(provider, model, job_id, input_tokens, output_tokens, cost_usd, duration_ms, status="ok"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO calls (ts, provider, model, job_id, input_tokens, output_tokens, cost_usd, duration_ms, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (int(datetime.now().timestamp() * 1000), provider, model, job_id,
          input_tokens, output_tokens, cost_usd, duration_ms, status))
    conn.commit()
    conn.close()


def get_monthly_spend() -> float:
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(cost_usd), 0)
        FROM calls
        WHERE strftime('%Y-%m', ts/1000, 'unixepoch') = strftime('%Y-%m', 'now')
          AND status != 'error'
    """).fetchone()
    conn.close()
    return row[0] or 0.0


def get_config() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def set_config(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_recent_calls(limit: int = 50):
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, ts, provider, model, job_id, input_tokens, output_tokens,
               cost_usd, duration_ms, status
        FROM calls ORDER BY ts DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_daily_spend(days: int = 30):
    conn = get_connection()
    cutoff = int((datetime.now().timestamp() - days * 86400) * 1000)
    rows = conn.execute("""
        SELECT
            strftime('%Y-%m-%d', ts/1000, 'unixepoch') as day,
            ROUND(SUM(cost_usd), 4) as total
        FROM calls
        WHERE ts > ? AND status != 'error'
        GROUP BY day
        ORDER BY day ASC
    """, (cutoff,)).fetchall()
    conn.close()
    return [{"day": row["day"], "total": row["total"]} for row in rows]


def get_stats() -> dict:
    config = get_config()
    spend  = get_monthly_spend()
    budget = float(config.get("monthly_budget_usd", 500))
    pct    = (spend / budget * 100) if budget > 0 else 0

    conn = get_connection()
    call_count = conn.execute("""
        SELECT COUNT(*) FROM calls
        WHERE strftime('%Y-%m', ts/1000, 'unixepoch') = strftime('%Y-%m', 'now')
    """).fetchone()[0]
    total_tokens = conn.execute("""
        SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM calls
        WHERE strftime('%Y-%m', ts/1000, 'unixepoch') = strftime('%Y-%m', 'now')
    """).fetchone()[0]
    conn.close()

    return {
        "spent_usd":    round(spend, 4),
        "budget_usd":   budget,
        "spent_pct":    round(pct, 1),
        "call_count":   call_count,
        "total_tokens": total_tokens,
        "config":       config,
    }