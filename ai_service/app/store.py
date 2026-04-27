from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .schemas import AIActionCard, AIMessageOut

# Per-session message history
session_store: dict[str, list[AIMessageOut]] = defaultdict(list)

# session_id → owner user_id
session_owner: dict[str, str] = {}

# user_id → most-recent session_id
user_last_session: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Persistent dict base — survives AI service restarts
# ---------------------------------------------------------------------------

class _PersistentDict(dict):
    """dict subclass that auto-saves to a JSON file on every mutation."""

    def __init__(self, path: Path, initial: dict | None = None) -> None:
        self._path = path
        super().__init__(initial or {})

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(dict(self)))
        except Exception:
            pass

    def __setitem__(self, key, value) -> None:
        super().__setitem__(key, value)
        self._save()

    def pop(self, key, *args):
        result = super().pop(key, *args)
        self._save()
        return result

    def update(self, other=(), **kwargs):  # type: ignore[override]
        super().update(other, **kwargs)
        self._save()


def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Persistent approval_store — pending approvals survive restarts
# ---------------------------------------------------------------------------

_APPROVAL_STORE_PATH = Path(__file__).parent.parent / "approval_store.json"

# action_id → {status, user_id, session_id, action_info}
approval_store: _PersistentDict = _PersistentDict(
    _APPROVAL_STORE_PATH, _load_json(_APPROVAL_STORE_PATH)
)


# ---------------------------------------------------------------------------
# Persistent action_thread_map — action_id → LangGraph turn_id
# ---------------------------------------------------------------------------

_THREAD_MAP_PATH = Path(__file__).parent.parent / "action_thread_map.json"

action_thread_map: _PersistentDict = _PersistentDict(
    _THREAD_MAP_PATH, _load_json(_THREAD_MAP_PATH)
)
