"""
bulk_test.py — Test the SERP agent with multiple keywords
----------------------------------------------------------
Run after starting the agent:  python serp_agent.py

Then in a second terminal:     python bulk_test.py
"""

import json
import time
import csv
import requests

BASE_URL = "http://localhost:8000"

# ── Edit these ──────────────────────────────────────
TARGET_WEBSITE = "flipkart.com"   # domain you want to track
COUNTRY        = "in"             # in = India, us = USA, uk = UK
PAGES_TO_SCAN  = 5                # 5 pages = top 50 results

KEYWORDS = [
    "running shoes",
    "bluetooth headphones",
    "laptop under 50000",
    "smartphone deals",
    "wireless earbuds",
    "gaming chair",
    "office chair",
    "smart tv 43 inch",
    "air purifier",
    "water purifier",
]
# ────────────────────────────────────────────────────


def check_single(keyword: str) -> dict:
    payload = {
        "keyword":    keyword,
        "target_url": TARGET_WEBSITE,
        "country":    COUNTRY,
        "pages":      PAGES_TO_SCAN,
    }
    try:
        resp = requests.post(f"{BASE_URL}/rank", json=payload, timeout=120)
        return resp.json()
    except Exception as e:
        return {"keyword": keyword, "error": str(e)}


def print_result(r: dict):
    rank = r.get("rank")
    kw   = r.get("keyword", "?")
    if r.get("error"):
        print(f"  ✗  {kw:<35} ERROR: {r['error']}")
    elif rank:
        print(f"  #{rank:<4} {kw:<35} {r.get('title','')[:50]}")
        print(f"        URL: {r.get('result_url','')}")
        if r.get("description"):
            print(f"        Desc: {r.get('description','')[:80]}...")
    else:
        print(f"  ---  {kw:<35} Not found in {r.get('pages_scanned',0)} pages")


def save_csv(results: list, filename="bulk_results.csv"):
    if not results:
        return
    keys = ["keyword", "rank", "country", "target_url", "result_url",
            "title", "description", "pages_scanned", "checked_at", "error"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"\n  Saved to {filename}")


if __name__ == "__main__":
    print(f"\nChecking {len(KEYWORDS)} keywords for '{TARGET_WEBSITE}' in {COUNTRY.upper()}\n")
    print("-" * 60)

    all_results = []
    for i, kw in enumerate(KEYWORDS, 1):
        print(f"[{i}/{len(KEYWORDS)}] Checking: {kw}")
        result = check_single(kw)
        print_result(result)
        all_results.append(result)
        if i < len(KEYWORDS):
            time.sleep(2)   # be polite

    print("\n" + "=" * 60)
    found = [r for r in all_results if r.get("rank")]
    print(f"  Summary: {len(found)}/{len(KEYWORDS)} keywords ranked")

    save_csv(all_results)