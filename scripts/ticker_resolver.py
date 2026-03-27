#!/usr/bin/env python3
import json
import re
import urllib.parse
import urllib.request

BRAND_MAP = {
    "WHOLE FOODS": {"parent": "Amazon", "ticker": "AMZN", "confidence": "high"},
    "WHOLEFDS": {"parent": "Amazon", "ticker": "AMZN", "confidence": "high"},
    "AMAZON": {"parent": "Amazon", "ticker": "AMZN", "confidence": "high"},
    "INSTAGRAM": {"parent": "Meta", "ticker": "META", "confidence": "high"},
    "FACEBOOK": {"parent": "Meta", "ticker": "META", "confidence": "high"},
    "WHATSAPP": {"parent": "Meta", "ticker": "META", "confidence": "high"},
    "GOOGLE": {"parent": "Alphabet", "ticker": "GOOGL", "confidence": "high"},
    "YOUTUBE": {"parent": "Alphabet", "ticker": "GOOGL", "confidence": "high"},
    "APPLE": {"parent": "Apple", "ticker": "AAPL", "confidence": "high"},
    "COSTCO": {"parent": "Costco", "ticker": "COST", "confidence": "high"},
    "TARGET": {"parent": "Target", "ticker": "TGT", "confidence": "high"},
    "WALMART": {"parent": "Walmart", "ticker": "WMT", "confidence": "high"},
    "MCDONALD": {"parent": "McDonald's", "ticker": "MCD", "confidence": "high"},
    "STARBUCKS": {"parent": "Starbucks", "ticker": "SBUX", "confidence": "high"},
    "UBER": {"parent": "Uber Technologies", "ticker": "UBER", "confidence": "high"},
    "LIVE NATION": {"parent": "Live Nation Entertainment", "ticker": "LYV", "confidence": "high"},
    "ALIBABA": {"parent": "Alibaba Group", "ticker": "BABA", "confidence": "high"},
    "LYFT": {"parent": "Lyft", "ticker": "LYFT", "confidence": "high"},
    "HOME DEPOT": {"parent": "Home Depot", "ticker": "HD", "confidence": "high"},
    "NIKE": {"parent": "Nike", "ticker": "NKE", "confidence": "high"},
    "NETFLIX": {"parent": "Netflix", "ticker": "NFLX", "confidence": "high"},
    "SPOTIFY": {"parent": "Spotify", "ticker": "SPOT", "confidence": "high"},
}

PUBLIC_HINTS = {
    "amazon": ("Amazon", "AMZN"),
    "alphabet": ("Alphabet", "GOOGL"),
    "google": ("Alphabet", "GOOGL"),
    "meta": ("Meta", "META"),
    "apple": ("Apple", "AAPL"),
    "microsoft": ("Microsoft", "MSFT"),
    "walmart": ("Walmart", "WMT"),
    "target": ("Target", "TGT"),
    "costco": ("Costco", "COST"),
    "nike": ("Nike", "NKE"),
    "uber": ("Uber Technologies", "UBER"),
    "lyft": ("Lyft", "LYFT"),
    "mcdonald": ("McDonald's", "MCD"),
    "starbucks": ("Starbucks", "SBUX"),
    "home depot": ("Home Depot", "HD"),
    "netflix": ("Netflix", "NFLX"),
    "spotify": ("Spotify", "SPOT"),
    "tesla": ("Tesla", "TSLA"),
    "nvidia": ("Nvidia", "NVDA"),
    "alibaba": ("Alibaba Group", "BABA"),
    "live nation": ("Live Nation Entertainment", "LYV"),
    "s&p 500": ("SPDR S&P 500 ETF Trust", "SPY"),
    "spy": ("SPDR S&P 500 ETF Trust", "SPY"),
}


def brave_search(query, api_key):
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": 5})
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("X-Subscription-Token", api_key)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def search_based_resolution(merchant_name, api_key=None):
    if not api_key:
        return None
    normalized_merchant = merchant_name.lower().strip()
    query = f"{merchant_name} stock ticker parent company site:wikipedia.org OR site:investopedia.com OR site:britannica.com"
    try:
        data = brave_search(query, api_key)
    except Exception:
        return None
    combined = []
    for item in (data.get("web", {}) or {}).get("results", []):
        title = item.get("title", "") or ""
        desc = item.get("description", "") or ""
        combined.append((title + " " + desc).lower())
    for hint, (parent, ticker) in PUBLIC_HINTS.items():
        mentions = sum(1 for text in combined if hint in text)
        merchant_overlap = hint in normalized_merchant or any(tok in hint for tok in normalized_merchant.split() if len(tok) > 3)
        if mentions >= 2 and merchant_overlap:
            return {"parent": parent, "ticker": ticker, "confidence": "medium", "source": "web-search"}
    return None


def resolve_merchant_to_ticker(normalized_name, display_name=None, brave_api_key=None):
    text = normalized_name.upper()
    for key, value in BRAND_MAP.items():
        if key in text:
            return {
                "merchantName": display_name or normalized_name.title(),
                "parentCompany": value["parent"],
                "ticker": value["ticker"],
                "confidence": value["confidence"],
                "resolutionSource": "brand-map",
                "orderDollars": 1,
            }
    resolved = search_based_resolution(display_name or normalized_name.title(), brave_api_key)
    if resolved:
        return {
            "merchantName": display_name or normalized_name.title(),
            "parentCompany": resolved["parent"],
            "ticker": resolved["ticker"],
            "confidence": resolved["confidence"],
            "resolutionSource": resolved["source"],
            "orderDollars": 1,
        }
    return None


if __name__ == "__main__":
    import os, sys
    merchant = sys.argv[1]
    print(json.dumps(resolve_merchant_to_ticker(merchant, merchant, os.getenv("BRAVE_API_KEY")), indent=2))
