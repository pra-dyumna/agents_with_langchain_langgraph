



import requests
from config import SERPER_API_KEY

def search_news(query: str):
    url = "https://google.serper.dev/news"

    payload = {"q": query}
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
    except Exception as e:
        return [{"error": str(e)}]

    articles = []
    for item in data.get("news", [])[:5]:
        articles.append({
            "title": item.get("title"),
            "source": item.get("source"),
            "link": item.get("link"),
            "date": item.get("date")
        })

    return articles
