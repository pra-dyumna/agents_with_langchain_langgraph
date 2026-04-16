"""
main.py
─────────────────────────────────────────────────────
Entry point. Runs a terminal chat loop using the compiled graph.

Usage:
  python main.py

Each user session gets a unique thread_id so state is kept
separate between different users / conversations.
"""

import uuid
from langchain_core.messages import HumanMessage, AIMessage

from langgraph_agents.supervisor_agent import compiled_graph


def chat_loop():
    # Each run gets a fresh session ID
    # In a real app you'd tie this to a user ID or session cookie
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 50)
    print("  Multi-Agent Assistant")
    print("  Commands: 'quit' to exit")
    print("=" * 50)
    print("Agent: Hello! I can help you with:")
    print("  • Create a bio       (say 'create my bio')")
    print("  • Get latest news    (ask about any topic)")
    print("  • Build daily routine (say 'build my routine')")
    print()

    while True:
        # ── Get user input ─────────────────────────────────────────────────
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Agent: Goodbye!")
            break

        # ── Invoke the graph ───────────────────────────────────────────────
        try:
            result = compiled_graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )
        except Exception as e:
            print(f"Agent: Sorry, something went wrong — {e}\n")
            continue

        # ── Print the last AI response ─────────────────────────────────────
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                print(f"Agent: {msg.content}\n")
                break


if __name__ == "__main__":
    chat_loop()