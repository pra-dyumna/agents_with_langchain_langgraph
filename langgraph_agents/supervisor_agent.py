"""
supervisor_agent.py
─────────────────────────────────────────────────────
The supervisor is the entry point for every user message.
It reads the message and decides which agent should handle it.

Routing logic:
  "bio" intent    →  parse_bio_input → bio_agent
  "news" intent   →  news_agent
  "routine" intent →  parse_routine_input → routine_agent

This file also contains:
  - The full graph assembly (all agents wired together)
  - The compiled graph you import in main.py / your chat loop
"""

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from langgraph_agents.state import AgentState
from langgraph_agents.llm_config.model_config import llm

# Import all agent nodes
from langgraph_agents.bio_agent     import parse_bio_input, bio_agent
from langgraph_agents.news_agent    import news_agent
from langgraph_agents.routine_agent import parse_routine_input, routine_agent


# ─────────────────────────────────────────────────────────────────────────────
# Node : supervisor
# Classifies the user's intent and stores it in state["intent"].
# ─────────────────────────────────────────────────────────────────────────────

def supervisor(state: AgentState) -> dict:
    messages = state.get("messages", [])

    if not messages:
        return {"intent": "unknown"}

    user_message = messages[-1].content.strip()

    # ── If intent is already set (mid-conversation), keep it ──────────────
    # This prevents re-routing mid bio/routine collection
    current_intent = state.get("intent")
    if current_intent in ("bio", "routine"):
        # Check if the task is complete before locking intent
        if current_intent == "bio" and state.get("bio"):
            pass   # bio done — allow re-routing on next message
        elif current_intent == "routine" and state.get("routine"):
            pass   # routine done — allow re-routing
        else:
            return {"intent": current_intent}   # still mid-collection

    # ── Use LLM to classify intent ─────────────────────────────────────────
    prompt = f"""You are a routing assistant. Read the user's message and 
output EXACTLY one word — nothing else:

  bio      → user wants to create a personal bio or profile
  news     → user wants news, current events, or information about a topic  
  routine  → user wants a daily routine, schedule, or time management help
  unknown  → does not match any of the above

User message: "{user_message}"

Output only one word:"""

    response = llm.invoke(prompt)
    raw = response if isinstance(response, str) else response.content
    intent = raw.strip().lower().split()[0]   # take first word only

    # Fallback if LLM returns something unexpected
    if intent not in ("bio", "news", "routine"):
        intent = "unknown"

    return {"intent": intent}


# ─────────────────────────────────────────────────────────────────────────────
# Conditional edge : route_after_supervisor
# Called after supervisor runs. Returns the name of the next node.
# ─────────────────────────────────────────────────────────────────────────────

def route_after_supervisor(
    state: AgentState,
) -> Literal["parse_bio_input", "news_agent", "parse_routine_input", "fallback"]:

    intent = state.get("intent", "unknown")

    if intent == "bio":
        return "parse_bio_input"
    elif intent == "news":
        return "news_agent"
    elif intent == "routine":
        return "parse_routine_input"
    else:
        return "fallback"


# ─────────────────────────────────────────────────────────────────────────────
# Node : fallback
# Handles unknown / unrecognised intents gracefully.
# ─────────────────────────────────────────────────────────────────────────────

def fallback(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(
            content=(
                "I can help you with:\n"
                "  • Create a bio — tell me 'create my bio'\n"
                "  • Get news     — ask about any topic\n"
                "  • Daily routine — say 'build my daily routine'\n\n"
                "What would you like to do?"
            )
        )]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Graph assembly
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Register all nodes ─────────────────────────────────────────────────
    graph.add_node("supervisor",          supervisor)
    graph.add_node("fallback",            fallback)

    # Bio agent nodes
    graph.add_node("parse_bio_input",     parse_bio_input)
    graph.add_node("bio_agent",           bio_agent)

    # News agent node
    graph.add_node("news_agent",          news_agent)

    # Routine agent nodes
    graph.add_node("parse_routine_input", parse_routine_input)
    graph.add_node("routine_agent",       routine_agent)

    # ── Entry point ────────────────────────────────────────────────────────
    graph.add_edge(START, "supervisor")

    # ── Supervisor routes to the right agent ───────────────────────────────
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "parse_bio_input":     "parse_bio_input",
            "news_agent":          "news_agent",
            "parse_routine_input": "parse_routine_input",
            "fallback":            "fallback",
        }
    )

    # ── Bio flow ───────────────────────────────────────────────────────────
    graph.add_edge("parse_bio_input", "bio_agent")
    graph.add_edge("bio_agent",       END)

    # ── News flow ──────────────────────────────────────────────────────────
    graph.add_edge("news_agent", END)

    # ── Routine flow ───────────────────────────────────────────────────────
    graph.add_edge("parse_routine_input", "routine_agent")
    graph.add_edge("routine_agent",       END)

    # ── Fallback ───────────────────────────────────────────────────────────
    graph.add_edge("fallback", END)

    return graph


# ─────────────────────────────────────────────────────────────────────────────
# Compile with MemorySaver
# MemorySaver keeps state alive between .invoke() calls using thread_id.
# This is what enables multi-turn bio and routine collection.
# ─────────────────────────────────────────────────────────────────────────────

checkpointer = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=checkpointer)