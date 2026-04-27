from __future__ import annotations

from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "agent_memory.db"


def get_checkpointer():
    """
    Returns a SQLite-backed checkpointer for persistent agent memory.
    Uses a direct sqlite3 connection so it works at module-level (no context manager needed).
    Falls back to MemorySaver if the sqlite package is unavailable.
    """
    try:
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        return SqliteSaver(conn)
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
