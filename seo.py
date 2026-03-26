# import requests
# import os
# from serpapi import GoogleSearch  # pip install google-search-results

# def get_rank(keyword, engine='google', country='us', language='en', target_domains=[]):
#     params = {
#         'api_key': os.getenv('SERPAPI_KEY'),
#         'q': keyword,
#         'engine': engine,
#         'gl': country,
#         'hl': language,
#         'num': 100
#     }
#     search = GoogleSearch(params)
#     results = search.get_dict()
#     organic = results.get('organic_results', [])

#     ranks = {}
#     for i, result in enumerate(organic, 1):
#         domain = result['link'].split('/')[2]
#         if domain in target_domains:
#             ranks[domain] = i
#             break  # First match
#     return ranks

# data=get_rank()



# import asyncio
# from playwright.async_api import async_playwright
# from fastapi import FastAPI
# import uvicorn
# from pydantic import BaseModel

# app = FastAPI()

# # REPLACE WITH YOUR WEB SHARE CREDENTIALS
# # USERNAME = "amzmlpkk"  # From webshare.io dashboard
# # PASSWORD = "62p6wlazfodh"
# # PROXIES = [f"http://{USERNAME}:{PASSWORD}@p.webshare.io:80"] * 3  # 3 free proxies
# PROXY_SERVER = "http://amzmlpkk:62p6wlazfodh@p.webshare.io:80"
# seo_no_proxy.py - COPY THIS - WORKS IMMEDIATELY
"""
SERP Rank Checker Agent
-----------------------
Finds your website's Google ranking for any keyword.
Returns rank, URL, title, description and full SEO details.

Usage:
  pip install -r requirements.txt
  playwright install chromium
  python serp_agent.py
"""

import asyncio
import csv
import io
import json
import re
import sqlite3
import time
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright
from pydantic import BaseModel

# ─────────────────────────────────────────────
#  CONFIG  (edit these)
# ─────────────────────────────────────────────

# Free Webshare proxies — sign up at https://webshare.io (free tier = 10 proxies)
# Set to [] to run WITHOUT proxies (fine for small-scale local testing)
WEBSHARE_USERNAME = "YOUR_WEBSHARE_USERNAME"
WEBSHARE_PASSWORD = "YOUR_WEBSHARE_PASSWORD"

# Free Webshare shared proxy endpoint
PROXY_HOST = "p.webshare.io"
PROXY_PORT = 80

USE_PROXIES = WEBSHARE_USERNAME != "YOUR_WEBSHARE_USERNAME"  # auto-disables if not configured

DB_PATH = "serp_results.db"
RESULTS_PER_PAGE = 10
REQUEST_DELAY_SECONDS = 2   # polite delay between page requests


# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at  TEXT,
            keyword     TEXT,
            country     TEXT,
            target_url  TEXT,
            rank        INTEGER,
            result_url  TEXT,
            title       TEXT,
            description TEXT,
            pages_scanned INTEGER
        )
    """)
    con.commit()
    con.close()


def save_result(row: dict):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO results
            (checked_at, keyword, country, target_url, rank, result_url, title, description, pages_scanned)
        VALUES
            (:checked_at, :keyword, :country, :target_url, :rank, :result_url, :title, :description, :pages_scanned)
    """, row)
    con.commit()
    con.close()


def fetch_history(limit: int = 100) -> list:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM results ORDER BY checked_at DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────

class RankRequest(BaseModel):
    keyword: str
    target_url: str                       # e.g. "flipkart.com" or "yourdomain.com"
    country: str = "in"                   # 2-letter country code: in, us, uk, au ...
    pages: int = 10                       # how many Google pages to scan (10 results each)
    language: str = "en"                  # hl parameter

class BulkRequest(BaseModel):
    jobs: List[RankRequest]


class SerpResult(BaseModel):
    keyword: str
    country: str
    target_url: str
    rank: Optional[int] = None            # None = not found in scanned pages
    result_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    pages_scanned: int = 0
    checked_at: str = ""
    error: Optional[str] = None


# ─────────────────────────────────────────────
#  SCRAPER
# ─────────────────────────────────────────────

def build_proxy_config() -> Optional[dict]:
    if not USE_PROXIES:
        return None
    return {
        "server":   f"http://{PROXY_HOST}:{PROXY_PORT}",
        "username": WEBSHARE_USERNAME,
        "password": WEBSHARE_PASSWORD,
    }


def build_google_url(keyword: str, country: str, language: str, page: int) -> str:
    start = page * RESULTS_PER_PAGE
    base  = f"https://www.google.com/search?q={keyword}&gl={country}&hl={language}&num=10"
    if start > 0:
        base += f"&start={start}"
    return base


def normalise_url(href: str) -> str:
    """Strip Google redirect wrapper /url?q=... and return the clean URL."""
    if href.startswith("/url?q="):
        href = href[7:]
        href = href.split("&")[0]
    return href


async def scrape_serp(request: RankRequest) -> SerpResult:
    """
    Open a headless browser, scrape Google SERP pages, return rank info.
    """
    proxy = build_proxy_config()
    checked_at = datetime.utcnow().isoformat()

    try:
        async with async_playwright() as pw:
            launch_args = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            }
            if proxy:
                launch_args["proxy"] = proxy

            browser = await pw.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale=f"{request.language}-{request.country.upper()}",
            )
            page = await context.new_page()

            # Hide automation fingerprints
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            global_rank   = 0   # running counter across pages
            found_rank    = None
            found_url     = None
            found_title   = None
            found_desc    = None
            pages_scanned = 0

            for page_num in range(request.pages):
                url = build_google_url(
                    request.keyword, request.country,
                    request.language, page_num
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await page.wait_for_timeout(1500)   # let JS settle
                except Exception:
                    break

                pages_scanned += 1

                # ── Extract organic results ──────────────────────────────────
                # Google renders results as <div class="g"> blocks
                # Each has an <a href>, an <h3> title, and a description span
                result_blocks = await page.query_selector_all("div.g, div[data-hveid]")

                page_results = []
                seen_urls = set()

                for block in result_blocks:
                    try:
                        link_el = await block.query_selector("a[href]")
                        if not link_el:
                            continue
                        href = await link_el.get_attribute("href") or ""
                        href = normalise_url(href)

                        # Skip non-http and internal Google links
                        if not href.startswith("http"):
                            continue
                        if "google.com" in href:
                            continue
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)

                        # Title
                        title_el = await block.query_selector("h3")
                        title = (await title_el.inner_text()).strip() if title_el else ""

                        # Description / snippet
                        desc_el = await block.query_selector(
                            "div[data-sncf], div.IsZvec, span.aCOpRe, div[style*='webkit-line-clamp']"
                        )
                        if not desc_el:
                            desc_el = await block.query_selector("div[class*='VwiC3b']")
                        desc = (await desc_el.inner_text()).strip() if desc_el else ""

                        page_results.append({
                            "url":   href,
                            "title": title,
                            "desc":  desc,
                        })
                    except Exception:
                        continue

                # ── Check if target is in this page's results ────────────────
                for item in page_results:
                    global_rank += 1
                    if request.target_url.lower() in item["url"].lower():
                        found_rank  = global_rank
                        found_url   = item["url"]
                        found_title = item["title"]
                        found_desc  = item["desc"]
                        break

                if found_rank is not None:
                    break

                # Polite delay between pages
                if page_num < request.pages - 1:
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)

            await browser.close()

        result = SerpResult(
            keyword      = request.keyword,
            country      = request.country,
            target_url   = request.target_url,
            rank         = found_rank,
            result_url   = found_url,
            title        = found_title,
            description  = found_desc,
            pages_scanned= pages_scanned,
            checked_at   = checked_at,
        )

        # Persist to DB
        save_result({
            "checked_at":    checked_at,
            "keyword":       request.keyword,
            "country":       request.country,
            "target_url":    request.target_url,
            "rank":          found_rank,
            "result_url":    found_url or "",
            "title":         found_title or "",
            "description":   found_desc or "",
            "pages_scanned": pages_scanned,
        })

        return result

    except Exception as exc:
        return SerpResult(
            keyword    = request.keyword,
            country    = request.country,
            target_url = request.target_url,
            checked_at = checked_at,
            error      = str(exc),
        )


# ─────────────────────────────────────────────
#  FASTAPI APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="SERP Rank Checker",
    description="Find your website's Google ranking for any keyword.",
    version="1.0.0",
)

init_db()


@app.get("/")
async def root():
    return {
        "status":    "SERP agent running",
        "endpoints": {
            "POST /rank":          "Check rank for one keyword",
            "POST /bulk":          "Check rank for many keywords",
            "GET  /history":       "View past results",
            "GET  /export/csv":    "Download all results as CSV",
        }
    }


@app.post("/rank", response_model=SerpResult)
async def check_rank(request: RankRequest):
    """
    Check Google ranking for a single keyword.

    Example body:
    {
      "keyword":    "running shoes",
      "target_url": "flipkart.com",
      "country":    "in",
      "pages":      5
    }
    """
    return await scrape_serp(request)


@app.post("/bulk")
async def bulk_check(request: BulkRequest):
    """
    Check rankings for multiple keywords sequentially.
    Returns list of results with rank, title, description.
    """
    results = []
    for job in request.jobs:
        result = await scrape_serp(job)
        results.append(result.dict())
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
    return {"total": len(results), "results": results}


@app.get("/history")
async def history(limit: int = 50):
    """Return the last N results from the database."""
    return {"results": fetch_history(limit)}


@app.get("/export/csv")
async def export_csv():
    """Download all results as a CSV file."""
    rows = fetch_history(limit=10_000)
    if not rows:
        return {"message": "No results yet."}

    output  = io.StringIO()
    writer  = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=serp_results.csv"},
    )


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  SERP Rank Checker — starting on http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print(f"  Proxies: {'ENABLED (Webshare)' if USE_PROXIES else 'DISABLED (direct)'}")
    print("=" * 50)
    uvicorn.run("serp_agent:app", host="0.0.0.0", port=8000, reload=False)