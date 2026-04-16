# from typing_extensions import TypedDict
# from langgraph.graph import StateGraph, START, END
# from IPython.display import Image, display
# from langgraph_agents.llm_config.model_config import llm
# import os

# API_KEY = os.getenv("GOOGLE_API_KEY")




# # llm = GoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, api_key=API_KEY)



# class AgentState(TypedDict):
#     name: str
#     age: int
#     Occupation: str
#     bio:str



# def generate_bio(state:AgentState):
#     name = state["name"]
#     age = state["age"]
#     occupation = state["Occupation"]
#     prompt = f"""Write a bio of the person based on the 
#     name :{name}
#     age: {age}
#     Occupation: {occupation}
#     """

#     response = llm.invoke(prompt)
#     print(response)
#     return {"bio": response}




# graph = StateGraph(AgentState)

# graph.add_node("generate_bio",generate_bio)
# graph.add_edge(START,"generate_bio")
# graph.add_edge("generate_bio", END)

# complied = graph.compile()

# # display(Image(complied.get_graph().draw_mermaid_png()))


# resposne = complied.invoke({"name": "Alice", "age": 30, "Occupation": "Software Engineer"})

# print(resposne)



"""
bio_agent.py
─────────────────────────────────────────────────────
Handles two jobs:

  1. parse_bio_input  — reads the user's reply and saves it to state
  2. bio_agent        — checks what's missing, asks for it, OR generates bio

Flow inside the graph:
  parse_bio_input → bio_agent → END   (repeats each turn until bio is done)
"""

from langchain_core.messages import AIMessage

from langgraph_agents.state import AgentState
from langgraph_agents.llm_config.model_config import llm


# ─────────────────────────────────────────────────────────────────────────────
# Node 1 : parse_bio_input
# Runs FIRST every turn. Reads the user's last message and decides
# which state field to save it into, based on what question was last asked.
# ─────────────────────────────────────────────────────────────────────────────

def parse_bio_input(state: AgentState) -> dict:
    messages = state.get("messages", [])

    # Need at least one message to parse
    if not messages:
        return {}

    user_reply = messages[-1].content.strip()

    # Find the last AI question so we know what the user was answering
    last_ai_question = ""
    for msg in reversed(messages[:-1]):   # skip the most recent human message
        if isinstance(msg, AIMessage):
            last_ai_question = msg.content.lower()
            break

    # ── Save name ──────────────────────────────────────────────────────────
    if "name" in last_ai_question and not state.get("name"):
        return {"name": user_reply}

    # ── Save age ───────────────────────────────────────────────────────────
    elif "age" in last_ai_question and not state.get("age"):
        try:
            return {"age": int(user_reply)}
        except ValueError:
            # User typed "thirty" instead of 30 — ask again
            return {
                "messages": [AIMessage(
                    content="Please enter your age as a number, e.g. 28"
                )]
            }

    # ── Save occupation ────────────────────────────────────────────────────
    elif ("work" in last_ai_question or "occupation" in last_ai_question or
          "do you do" in last_ai_question) and not state.get("occupation"):
        return {"occupation": user_reply}

    # First turn or unrecognised — nothing to save yet
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Node 2 : bio_agent
# Runs SECOND every turn. Checks state and either:
#   - Asks for the next missing piece of info, OR
#   - Generates the bio if all info is collected
# ─────────────────────────────────────────────────────────────────────────────

def bio_agent(state: AgentState) -> dict:

    # ── Step 1: ask for name if missing ───────────────────────────────────
    if not state.get("name"):
        return {
            "messages": [AIMessage(
                content="Sure! I'll help you create a bio. What's your name?"
            )]
        }

    # ── Step 2: ask for age if missing ────────────────────────────────────
    if not state.get("age"):
        return {
            "messages": [AIMessage(
                content=f"Nice to meet you, {state['name']}! How old are you?"
            )]
        }

    # ── Step 3: ask for occupation if missing ─────────────────────────────
    if not state.get("occupation"):
        return {
            "messages": [AIMessage(
                content="What do you do for work or what is your occupation?"
            )]
        }

    # ── Step 4: all info collected — generate the bio ─────────────────────
    prompt = f"""Write a short, engaging professional bio for this person:

Name:       {state['name']}
Age:        {state['age']}
Occupation: {state['occupation']}

The bio should be 3-4 sentences, written in third person, and sound natural.
"""
    response = llm.invoke(prompt)
    bio_text = response if isinstance(response, str) else response.content

    return {
        "bio": bio_text,
        "messages": [AIMessage(content=f"Here is your bio:\n\n{bio_text}")]
    }