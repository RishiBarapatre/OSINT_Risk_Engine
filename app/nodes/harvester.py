import urllib.request
import urllib.parse
import json
import logging
import feedparser
import yfinance as yf
from app.state import OSINTState

# Set up logging
logging.basicConfig(level=logging.INFO)


def fetch_financials_sync(ticker: str) -> dict:
    """Fetches key balance sheet and financial risk metrics using yfinance with safe null-handling."""
    if not ticker:
        return {}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        raw_metrics = {
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "profit_margins": info.get("profitMargins"),
            "operating_margins": info.get("operatingMargins"),
            "pe_ratio": info.get("trailingPE"),
            "price_to_book": info.get("priceToBook"),
        }

        # Convert None values to explicit human/LLM-readable labels
        cleaned_metrics = {
            k: (v if v is not None else "N/A (Not reported for this asset type)")
            for k, v in raw_metrics.items()
        }

        return cleaned_metrics
    except Exception as e:
        logging.error(f"yfinance error for ticker {ticker}: {str(e)}")
        return {"error": f"Failed to fetch financial metrics: {str(e)}"}

import html

def fetch_news_sync(company_name: str, max_results: int = 7) -> list:
    """Fetches targeted news using Google News RSS with unescaping and deduplication."""
    try:
        encoded_company = urllib.parse.quote(company_name)
        queries = [
            f"{encoded_company}%20financial%20performance",
            f"{encoded_company}%20(lawsuit%20OR%20antitrust%20OR%20SEC%20OR%20DOJ%20OR%20penalty%20OR%20fraud)",
        ]

        articles = []
        seen_headlines = set()

        for q in queries:
            rss_url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:max_results]:
                # Clean HTML entities (e.g. &amp; -> &, &#39; -> ')
                raw_title = entry.get("title", "")
                clean_headline = html.unescape(raw_title)

                # Deduplicate based on cleaned headline string
                if clean_headline not in seen_headlines:
                    seen_headlines.add(clean_headline)
                    articles.append({
                        "headline": clean_headline,
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })

        return articles
    except Exception as e:
        logging.error(f"Google News RSS error: {str(e)}")
        return [{"error": f"Failed to fetch news: {str(e)}"}]

def fetch_sec_filings_sync(ticker: str) -> list:
    """
    Fetches the latest material events (8-K filings) from the US SEC EDGAR API
    and decodes Item codes into plain English risk events.
    """
    if not ticker:
        return []

    ITEM_MAPPING = {
        "1.01": "Entry into a Material Definitive Agreement",
        "1.02": "Termination of a Material Definitive Agreement",
        "1.03": "Bankruptcy or Receivership",
        "1.04": "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
        "1.05": "Material Cybersecurity Incidents (Data Breach/Hack)",
        "2.01": "Completion of Acquisition or Disposition of Assets",
        "2.02": "Results of Operations and Financial Condition (Earnings Release)",
        "2.03": "Creation of a Direct Financial Obligation",
        "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
        "2.05": "Costs Associated with Exit or Disposal Activities (Layoffs/Restructuring)",
        "2.06": "Material Impairments",
        "3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule",
        "3.02": "Unregistered Sales of Equity Securities",
        "4.01": "Changes in Registrant's Certifying Accountant (Auditor Resigned/Dismissed)",
        "4.02": "Non-Reliance on Previously Issued Financial Statements (Accounting Error/Fraud)",
        "5.01": "Changes in Control of Registrant",
        "5.02": "Departure of Directors or Certain Officers (Executive Resigned/Fired)",
        "7.01": "Regulation FD Disclosure",
        "8.01": "Other Material Events",
        "9.01": "Financial Statements and Exhibits",
    }

    try:
        headers = {
            "User-Agent": "DataScience Portfolio Project (your.email@example.com)"
        }

        # 1. Map ticker to SEC CIK
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        req = urllib.request.Request(tickers_url, headers=headers)

        with urllib.request.urlopen(req) as response:
            tickers_data = json.loads(response.read().decode())

        cik_str = None
        for key, value in tickers_data.items():
            if value.get("ticker") == ticker.upper():
                cik_str = str(value.get("cik_str")).zfill(10)
                break

        if not cik_str:
            return [{"error": f"Could not find SEC CIK for ticker {ticker}"}]

        # 2. Fetch submissions
        filings_url = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
        req = urllib.request.Request(filings_url, headers=headers)

        with urllib.request.urlopen(req) as response:
            company_data = json.loads(response.read().decode())

        recent_filings = company_data.get("filings", {}).get("recent", {})

        extracted_8ks = []
        forms = recent_filings.get("form", [])
        dates = recent_filings.get("filingDate", [])
        items_list = recent_filings.get("items", [])

        # 3. Filter 8-Ks
        for i, form in enumerate(forms):
            if form == "8-K":
                raw_items = items_list[i] if i < len(items_list) else ""

                decoded_events = []
                if raw_items:
                    for item_num in raw_items.split(","):
                        item_num = item_num.strip()
                        if item_num in ITEM_MAPPING:
                            decoded_events.append(ITEM_MAPPING[item_num])
                        else:
                            decoded_events.append(f"Item {item_num}")

                description = (
                    " | ".join(decoded_events)
                    if decoded_events
                    else "Unspecified Material Event"
                )

                extracted_8ks.append(
                    {
                        "date": dates[i],
                        "type": "SEC Form 8-K",
                        "event_details": description,
                    }
                )

            if len(extracted_8ks) >= 3:
                break

        return extracted_8ks

    except Exception as e:
        logging.error(f"SEC API Error: {str(e)}")
        return [{"error": f"Failed to fetch SEC filings: {str(e)}"}]


import asyncio

async def harvester_node(state: OSINTState) -> OSINTState:
    """LangGraph node that collects data concurrently across all OSINT sources."""
    print(f"[*] Harvesting data concurrently for: {state.query}...")

    # Define tasks to run in parallel threads
    tasks = []
    
    # Task 1: Financials
    if state.ticker_symbol:
        tasks.append(asyncio.to_thread(fetch_financials_sync, state.ticker_symbol))
    else:
        tasks.append(asyncio.sleep(0))  # Placeholder if no ticker

    # Task 2: News
    tasks.append(asyncio.to_thread(fetch_news_sync, state.query))

    # Task 3: SEC Filings
    if state.ticker_symbol:
        tasks.append(asyncio.to_thread(fetch_sec_filings_sync, state.ticker_symbol))
    else:
        tasks.append(asyncio.sleep(0))  # Placeholder if no ticker

    # Execute all 3 network calls concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Assign results safely
    if state.ticker_symbol and not isinstance(results[0], Exception):
        state.financial_data = results[0]
        
    if not isinstance(results[1], Exception):
        state.news_data = results[1]
        
    if state.ticker_symbol and not isinstance(results[2], Exception):
        state.sec_filings = results[2]

    print("[*] Concurrent harvesting complete.")
    return state