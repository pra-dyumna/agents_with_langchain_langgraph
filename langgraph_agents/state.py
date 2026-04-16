from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Supervisor ────────────────────────────────
    intent: Optional[str]          # "bio" | "news" | "routine"

    # ── Bio Agent fields ──────────────────────────
    name:       Optional[str]
    age:        Optional[int]
    occupation: Optional[str]
    bio:        Optional[str]

    # ── News Agent fields ─────────────────────────
    news_results: Optional[str]

    # ── Routine Agent fields ──────────────────────
    routine: Optional[str]

    # ── Shared chat history ───────────────────────
    # add_messages tells LangGraph to APPEND, not overwrite
    messages: Annotated[list, add_messages]