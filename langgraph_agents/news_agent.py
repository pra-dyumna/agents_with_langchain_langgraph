"""
news_agent.py
─────────────────────────────────────────────────────
Handles one job:

  news_agent — takes the user's query, searches Tavily,
               formats the results, returns them as a message.

This is a simple single-node agent (no loop needed).
The user asks → Tavily searches → results returned. Done.
"""

import os
from langchain_core.messages import AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults

from langgraph_agents.state import AgentState


# ─────────────────────────────────────────────────────────────────────────────
# Tavily tool setup
# Make sure TAVILY_API_KEY is set in your environment:
#   export TAVILY_API_KEY="tvly-your-key-here"
# ─────────────────────────────────────────────────────────────────────────────

tavily = TavilySearchResults(
    max_results=3,
    search_depth="advanced",   # "basic" is faster, "advanced" is richer
    include_answer=True,       # gives a direct answer snippet at the top
)


# ─────────────────────────────────────────────────────────────────────────────
# Node : news_agent
# ─────────────────────────────────────────────────────────────────────────────

def news_agent(state: AgentState) -> dict:
    messages = state.get("messages", [])

    # Pull the user's query from the last message
    if not messages:
        return {
            "messages": [AIMessage(
                content="What topic would you like news about?"
            )]
        }

    query = messages[-1].content.strip()

    # ── Call Tavily ────────────────────────────────────────────────────────
    try:
        results = tavily.invoke({"query": query})
    except Exception as e:
        return {
            "messages": [AIMessage(
                content=f"Sorry, I couldn't fetch news right now. Error: {e}"
            )]
        }

    # ── Handle empty results ───────────────────────────────────────────────
    if not results:
        return {
            "messages": [AIMessage(
                content=f"I couldn't find any recent news about '{query}'."
            )]
        }

    # ── Format results neatly ──────────────────────────────────────────────
    # Each result dict has: title, url, content, score
    lines = []
    for i, result in enumerate(results, start=1):
        title   = result.get("title", "No title")
        url     = result.get("url", "")
        snippet = result.get("content", "")[:250].strip()
        lines.append(f"{i}. {title}\n   {snippet}...\n   {url}")

    formatted = "\n\n".join(lines)
    reply = f"Here's the latest news on **{query}**:\n\n{formatted}"

    return {
        "news_results": formatted,
        "messages": [AIMessage(content=reply)]
    }