"""
routine_agent.py
─────────────────────────────────────────────────────
Handles two jobs:

  1. parse_routine_input  — checks if we have enough info to build a routine
  2. routine_agent        — asks clarifying questions OR generates the routine

Flow inside the graph:
  parse_routine_input → routine_agent → END

The agent needs to know:
  - wake_time    : e.g. "6 AM"
  - sleep_time   : e.g. "11 PM"
  - goals        : e.g. "exercise, deep work, reading"

Once all three are collected, it builds a structured daily plan.
"""

from langchain_core.messages import AIMessage

from langgraph_agents.state import AgentState
from langgraph_agents.llm_config.model_config import llm


# We store routine sub-fields inside the shared state's messages context.
# To keep AgentState clean, we track collected routine info in a simple
# helper that reads from the conversation history.

def _get_routine_context(state: AgentState) -> dict:
    """
    Scan message history for routine sub-answers that were previously saved.
    Returns a dict with keys: wake_time, sleep_time, goals (any can be None).
    """
    context = {"wake_time": None, "sleep_time": None, "goals": None}

    messages = state.get("messages", [])
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            q = msg.content.lower()
            # Look at the NEXT human message as the answer
            if i + 1 < len(messages):
                answer = messages[i + 1].content.strip()
                if "wake" in q and context["wake_time"] is None:
                    context["wake_time"] = answer
                elif "sleep" in q or "bed" in q:
                    if context["sleep_time"] is None:
                        context["sleep_time"] = answer
                elif "goal" in q or "focus" in q or "want to achieve" in q:
                    if context["goals"] is None:
                        context["goals"] = answer

    return context


# ─────────────────────────────────────────────────────────────────────────────
# Node 1 : parse_routine_input
# Reads the conversation to check what routine info has been collected so far.
# Does not save anything — just passes through; routine_agent does the logic.
# ─────────────────────────────────────────────────────────────────────────────

def parse_routine_input(state: AgentState) -> dict:
    # Nothing to extract here — _get_routine_context() reads from messages.
    # This node is a placeholder that could do pre-processing if needed.
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Node 2 : routine_agent
# Asks for missing info one question at a time.
# Once all 3 pieces are collected, generates a full daily routine.
# ─────────────────────────────────────────────────────────────────────────────

def routine_agent(state: AgentState) -> dict:
    ctx = _get_routine_context(state)

    wake_time  = ctx["wake_time"]
    sleep_time = ctx["sleep_time"]
    goals      = ctx["goals"]

    # ── Step 1: ask for wake time ──────────────────────────────────────────
    if not wake_time:
        return {
            "messages": [AIMessage(
                content=(
                    "I'll help you build a daily routine! "
                    "What time do you usually wake up? (e.g. 6:00 AM)"
                )
            )]
        }

    # ── Step 2: ask for sleep time ─────────────────────────────────────────
    if not sleep_time:
        return {
            "messages": [AIMessage(
                content=(
                    f"Got it — wake up at {wake_time}. "
                    "What time do you usually go to bed? (e.g. 10:30 PM)"
                )
            )]
        }

    # ── Step 3: ask for goals ──────────────────────────────────────────────
    if not goals:
        return {
            "messages": [AIMessage(
                content=(
                    "What are your main goals or focus areas for the day? "
                    "(e.g. exercise, deep work, reading, family time)"
                )
            )]
        }

    # ── Step 4: all info collected — generate the routine ──────────────────
    prompt = f"""You are a professional time management coach.

Build a practical, realistic daily routine for someone with these details:
  Wake time : {wake_time}
  Sleep time: {sleep_time}
  Goals     : {goals}

Format the routine as a clear time-block schedule like:
  6:00 AM  - Wake up & hydrate (10 min)
  6:10 AM  - Morning exercise (30 min)
  ...

Rules:
- Every block should have a duration
- Include breaks, meals, and wind-down time
- Group deep work in the morning when energy is highest
- Keep it realistic — don't over-schedule
- End with 2-3 practical tips for sticking to this routine
"""

    response = llm.invoke(prompt)
    routine_text = response if isinstance(response, str) else response.content

    return {
        "routine": routine_text,
        "messages": [AIMessage(
            content=f"Here's your personalised daily routine:\n\n{routine_text}"
        )]
    }