"""对话历史的存储层。只负责读写数据库，不管业务。"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "chat.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id);
"""


@contextmanager
def _connect():
    """一次连接的完整生命周期：正常结束提交，出错回滚，无论如何关闭。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """启动时调一次，建表。重复调用安全。"""
    with _connect() as conn:
        conn.executescript(SCHEMA)


def new_session_id():
    return uuid.uuid4().hex


def save_message(session_id, role, content):
    """存一条消息。"""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat(timespec="seconds")),
        )


def get_history(session_id, limit=20):
    """取最近 limit 条，按时间正序，返回 [{"role":…, "content":…}]。
    这个格式可以直接传给 rag_qa.ask(history=…)。
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()

    # SQL 按 id 倒序取"最近 N 条"，这里翻回正序（老 → 新）
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_messages(session_id):
    """给 GET /history 用：全部消息，正序，带时间。"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_session(session_id):
    """删掉一个会话的所有消息，返回删了几条。"""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        return cur.rowcount