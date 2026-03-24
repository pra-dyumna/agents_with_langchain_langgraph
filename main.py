from google import genai
from google.genai import types
import json
from tools import search_news
from config import GOOGLE_GENAI_API_KEY

client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)



tools = [
    {
        "name": "search_news",
        "description": "Fetch latest news about AI, tech, or any topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]



def clean_json(text: str):
    text = text.strip()
    # remove markdown ```json ```
    if text.startswith("```"):
        text = text.split("```")[1]  # remove first ```
        text = text.replace("json", "")  # remove json word
        text = text.strip()

    return text


def decide_tool(user_input: str):
    prompt = f"""
You are an AI agent.

IMPORTANT RULES:
- You MUST use ONLY this tool name: "search_news"
- DO NOT use any other name like search, browser, google_search

Return ONLY JSON:

{{
  "tool": "search_news",
  "arguments": {{
    "query": "<query>"
  }}
}}

User: {user_input}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",  # 🔥 KEY LINE
            response_schema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }
            }
        )
    )

    return response.parsed  # ✅ already JSON

def execute_tool(decision):
    if decision["tool"] == "search_news":
        return search_news(**decision["arguments"])

    raise ValueError("Invalid tool")


def safe_decide(user_input, retries=3):
    for _ in range(retries):
        try:
            return decide_tool(user_input)
        except Exception:
            continue
    raise Exception("LLM failed after retries")


def run_agent(user_input: str):
    decision = safe_decide(user_input)

    print("[DECISION]:", decision)

    if decision["tool"] == "search_news":
        result = search_news(**decision["arguments"])

        final = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
User: {user_input}

Data:
{result}

Summarize nicely.
"""
        )
        print("234245",final)

        return final.text

    return "No tool needed"


while True:
    user = input("You: ")
    print("Agent:", run_agent(user))
