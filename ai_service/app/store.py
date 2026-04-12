from collections import defaultdict

from .schemas import AIActionCard, AIMessageOut

# Per-session message history
session_store: dict[str, list[AIMessageOut]] = defaultdict(list)

# session_id → owner user_id
session_owner: dict[str, str] = {}

# user_id → most-recent session_id
user_last_session: dict[str, str] = {}

# action_id → approval info (status, user_id, action_card)
approval_store: dict[str, dict[str, str | AIActionCard]] = {}

# action_id → LangGraph thread_id (turn_id) — used to resume interrupted graphs
action_thread_map: dict[str, str] = {}
