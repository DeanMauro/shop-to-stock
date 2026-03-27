#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from collections import defaultdict

from ticker_resolver import resolve_merchant_to_ticker
from public_quotes import get_equity_quotes
from public_portfolio import get_portfolio_snapshot

TELLER_API = "https://api.teller.io"

EXCLUDE_PATTERNS = [
    r"\bATM\b", r"\bWITHDRAWAL\b", r"\bTRANSFER\b", r"\bACH\b", r"\bPAYROLL\b",
    r"\bZELLE\b", r"\bVENMO\b", r"CASH APP", r"APPLE CASH", r"\bFEE\b",
    r"\bINTEREST\b", r"\bREVERSAL\b", r"\bADJUSTMENT\b"
]
PROCESSOR_PREFIXES = [r"^SQ \*", r"^PAYPAL \*", r"^TST\*", r"^POS ", r"^DBTCRD "]


def env(name, required=True, default=None):
    value = os.getenv(name, default)
    if required and not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def target_day(day=None):
    if day:
        return dt.date.fromisoformat(day)
    return dt.date.today() - dt.timedelta(days=1)


def teller_ssl_context():
    cert = env("TELLER_CERT_FILE")
    key = env("TELLER_KEY_FILE")
    ctx = ssl.create_default_context()
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    return ctx


def teller_request(path):
    token = env("TELLER_ACCESS_TOKEN")
    req = urllib.request.Request(f"{TELLER_API}{path}")
    auth = base64.b64encode(f"{token}:".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Teller-Version", "2020-10-12")
    with urllib.request.urlopen(req, context=teller_ssl_context()) as resp:
        return json.loads(resp.read().decode())


def fetch_accounts():
    return teller_request("/accounts")


def fetch_transactions(account_id, day):
    q = urllib.parse.urlencode({"count": 500})
    items = teller_request(f"/accounts/{account_id}/transactions?{q}")
    out = []
    for tx in items:
        date_str = tx.get("date")
        if not date_str:
            continue
        if dt.date.fromisoformat(date_str) == day:
            out.append(tx)
    return out


def merchant_name(tx):
    merchant = tx.get("merchant") or {}
    details = tx.get("details") or {}
    counterparty = details.get("counterparty") or {}

    candidates = [
        merchant.get("name"),
        counterparty.get("name"),
        tx.get("description"),
        details.get("description"),
    ]
    for candidate in candidates:
        if candidate and str(candidate).strip():
            return str(candidate).strip()

    processing_status = details.get("processing_status")
    if processing_status and str(processing_status).strip():
        return str(processing_status).strip()
    return "Unknown"


def exclusion_reason(tx):
    text = " ".join(filter(None, [tx.get("description"), json.dumps(tx.get("merchant") or {}), json.dumps(tx.get("details") or {})])).upper()
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, text):
            return f"matched exclusion pattern {pat}"
    category = str((tx.get("details") or {}).get("category") or "").upper()
    if any(word in category for word in ["TRANSFER", "ATM", "DEPOSIT"]):
        return f"excluded category {category}"
    amount = tx.get("amount")
    if amount is None or float(amount) <= 0:
        return "not a spending transaction"
    return ""


def normalize_merchant(raw):
    s = (raw or "").upper().strip()
    if not s:
        return ""
    for pat in PROCESSOR_PREFIXES:
        s = re.sub(pat, "", s)
    s = re.sub(r"AMZN MKT[P]? US\*.*", "AMAZON", s)
    s = re.sub(r"APPLE\.COM/BILL.*", "APPLE", s)
    s = re.sub(r"WHOLEFDS.*", "WHOLE FOODS", s)
    s = re.sub(r"UBER\s+\*?TRIP.*", "UBER", s)
    s = re.sub(r"[^A-Z0-9&' ]+", " ", s)
    s = re.sub(r"\b(?:NEW YORK|NY|BROOKLYN|BKLYN|CA|SAN FRANCISCO|SEATTLE|AUSTIN)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def display_name(normalized):
    return " ".join(p.capitalize() for p in normalized.split())


def tx_id(tx):
    return tx.get('id') or tx.get('transaction_id') or tx.get('transactionId') or tx.get('description') or 'unknown'


def aggregate_transactions(transactions):
    grouped = defaultdict(lambda: {"totalSpent": 0.0, "transactions": [], "rawNames": set(), "txIds": []})
    skipped = []
    for tx in transactions:
        raw_name = merchant_name(tx)
        reason = exclusion_reason(tx)
        if reason:
            skipped.append({"name": raw_name, "reason": reason})
            continue
        normalized = normalize_merchant(raw_name)
        if not normalized:
            skipped.append({"name": raw_name, "reason": "could not normalize merchant"})
            continue
        grouped[normalized]["totalSpent"] += float(tx.get("amount", 0))
        grouped[normalized]["transactions"].append(tx)
        grouped[normalized]["rawNames"].add(raw_name)
        grouped[normalized]["txIds"].append(tx_id(tx))
    merchants = []
    for normalized, data in grouped.items():
        merchants.append({
            "name": display_name(normalized),
            "normalized": normalized,
            "totalSpent": round(data["totalSpent"], 2),
            "transactionCount": len(data["transactions"]),
            "transactionIds": data["txIds"],
            "primaryTransactionId": data["txIds"][0] if data["txIds"] else 'unknown',
            "rawNames": sorted(data["rawNames"]),
        })
    merchants.sort(key=lambda x: x["totalSpent"], reverse=True)
    return merchants, skipped


def demo_transactions(day):
    sample = [
        ("txn_pqbbbtbpamzn5ge8tg3i001", "AMZN Mktp US*AB12", 84.27),
        ("txn_pqbbbtbpuber5ge8tg3i002", "PAYPAL *UBER", 26.14),
        ("txn_pqbbbtbpsbux5ge8tg3i003", "STARBUCKS 1234", 12.85),
        ("txn_pqbbbtbplyv05ge8tg3i004", "LIVE NATION TICKETS", 149.50),
        ("txn_pqbbbtbpbaba5ge8tg3i005", "ALIBABA.COM", 63.40),
        ("txn_pqbbbtbpwegm5ge8tg3i006", "WEGMANS", 54.21),
        ("txn_pqbbbtbpbagl5ge8tg3i007", "CLIFTON BAGELS", 18.90),
        ("txn_pqbbbtbpbars5ge8tg3i008", "J&R SPORTS BAR", 37.60),
        ("txn_pqbbbtbpbake5ge8tg3i009", "DA VINCI BAKERY", 22.75),
    ]
    return [
        {
            "id": txid,
            "date": day.isoformat(),
            "amount": amount,
            "description": name,
            "merchant": {"name": name},
            "details": {"category": "card_payment"},
        }
        for txid, name, amount in sample
    ]


def build_plan(day, use_demo=False):
    brave_api_key = os.getenv("BRAVE_API_KEY")
    source_day = day
    fallback_to_latest = False
    if use_demo:
        transactions = demo_transactions(day)
    else:
        accounts = fetch_accounts()
        transactions = []
        accounts_to_scan = []
        for acct in accounts:
            if acct.get("type") not in {"depository", "credit"}:
                continue
            acct_id = acct.get("id")
            if acct_id:
                accounts_to_scan.append(acct_id)
                transactions.extend(fetch_transactions(acct_id, day))
        merchants_preview, _ = aggregate_transactions(transactions)
        if not merchants_preview and accounts_to_scan:
            latest_by_date = {}
            for acct_id in accounts_to_scan:
                q = urllib.parse.urlencode({"count": 500})
                items = teller_request(f"/accounts/{acct_id}/transactions?{q}")
                for tx in items:
                    date_str = tx.get("date")
                    if not date_str:
                        continue
                    try:
                        tx_day = dt.date.fromisoformat(date_str)
                    except ValueError:
                        continue
                    latest_by_date.setdefault(tx_day, []).append(tx)
            useful_days = []
            for candidate_day, txs in latest_by_date.items():
                merchants_candidate, _ = aggregate_transactions(txs)
                if merchants_candidate:
                    useful_days.append(candidate_day)
            if useful_days:
                source_day = max(useful_days)
                fallback_to_latest = source_day != day
                transactions = latest_by_date[source_day]
    merchants, skipped = aggregate_transactions(transactions)
    picks, unresolved = [], []
    seen_tickers = set()
    for merchant in merchants:
        resolved = resolve_merchant_to_ticker(merchant["normalized"], merchant["name"], brave_api_key)
        if not resolved:
            unresolved.append({"name": merchant["name"], "reason": "no high-confidence public parent ticker found"})
            continue
        if resolved["ticker"] in seen_tickers:
            unresolved.append({"name": merchant["name"], "reason": f"duplicate parent ticker {resolved['ticker']}"})
            continue
        resolved["merchantSpend"] = merchant["totalSpent"]
        picks.append(resolved)
        seen_tickers.add(resolved["ticker"])
        if len(picks) >= 5:
            break
    fallback_needed = max(0, 5 - len(picks))
    if fallback_needed:
        picks.append({
            'merchantName': 'S&P 500',
            'parentCompany': 'SPDR S&P 500 ETF Trust',
            'ticker': 'SPY',
            'confidence': 'fallback',
            'resolutionSource': 'fallback',
            'orderDollars': fallback_needed,
            'merchantSpend': 0,
            'orderStatus': 'pending',
            'isFallback': True,
        })
    quotes = get_equity_quotes([p['ticker'] for p in picks]) if picks else {}
    for pick in picks:
        price = quotes.get(pick['ticker'])
        pick['currentPrice'] = price
        pick['estimatedShares'] = round(float(pick.get('orderDollars', 1)) / price, 6) if price and price > 0 else None
        pick['orderStatus'] = pick.get('orderStatus', 'pending')
    public_by_normalized = {normalize_merchant(p["merchantName"]): p for p in picks if not p.get('isFallback')}
    combined = []
    for merchant in merchants[:10]:
        matched = public_by_normalized.get(merchant["normalized"])
        combined.append({
            "merchantName": merchant["name"],
            "normalized": merchant["normalized"],
            "totalSpent": merchant["totalSpent"],
            "transactionCount": merchant["transactionCount"],
            "transactionId": merchant["primaryTransactionId"],
            "date": source_day.isoformat(),
            "public": bool(matched),
            "label": "Public" if matched else "Non-public / skipped",
            "buy": matched or None,
            "orderStatus": matched.get('orderStatus') if matched else 'not eligible',
        })
    combined.sort(key=lambda e: (0 if e['public'] else 1, -float(e['totalSpent'])))
    fallback_entries = []
    for pick in picks:
        if pick.get('isFallback'):
            fallback_entries.append({
                'merchantName': 'S&P 500',
                'normalized': 'SPY_FALLBACK',
                'totalSpent': 0,
                'transactionCount': 0,
                'transactionId': 'fallback',
                'date': source_day.isoformat(),
                'public': True,
                'label': 'Fallback investment',
                'buy': pick,
                'orderStatus': pick.get('orderStatus', 'pending'),
                'isFallback': True,
            })
    combined.extend(fallback_entries)
    explanation = "Investing doesn’t take days off! Since there weren’t enough purchases today, we’re going to invest in the trusty S&P 500!" if fallback_needed else "Below are your purchases for the past day. Any publicly traded companies you bought from have been identified so we can invest in them."
    if fallback_to_latest:
        explanation += f" We’re still publishing today’s diary, but using the latest useful available transaction data from {source_day.isoformat()}."
    return {
        "date": day.isoformat(),
        "displayDate": day.strftime('%A: %B %d, %Y'),
        "totals": {
            "merchantSpend": round(sum(m["totalSpent"] for m in merchants), 2),
            "plannedInvest": round(sum(float(p.get("orderDollars", 1)) for p in picks), 2),
            "executedInvest": 0,
        },
        "entries": combined,
        "topExplanation": explanation,
        "merchants": merchants[:10],
        "skipped": (skipped + unresolved)[:30],
        "picks": picks,
        "orders": [],
        "generatedAt": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "confirmationRequired": True,
        "demoMode": use_demo,
        "sourceTransactionDate": source_day.isoformat(),
        "usedLatestAvailableTransactions": fallback_to_latest,
        "connected": bool(os.getenv("TELLER_ACCESS_TOKEN")) or use_demo,
        "logoDevConfigured": bool(os.getenv("LOGO_DEV_TOKEN")),
        "portfolio": get_portfolio_snapshot(),
    }


def kv_put(key, value):
    account_id = env("CLOUDFLARE_ACCOUNT_ID")
    namespace = env("CLOUDFLARE_KV_NAMESPACE_ID")
    token = env("CLOUDFLARE_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace}/values/{urllib.parse.quote(key, safe='')}"
    req = urllib.request.Request(url, data=value.encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return resp.status


def publish_summary(plan):
    kv_put(f"summary:{plan['date']}", json.dumps(plan))
    kv_put("status:latest-pending-diary", json.dumps({
        "date": plan["date"],
        "link": f"{env('SHOP_TO_STOCK_BASE_URL').rstrip('/')}/d/{plan['date']}",
        "confirmationRequired": bool(plan.get("confirmationRequired", True)),
        "generatedAt": plan.get("generatedAt"),
        "totals": plan.get("totals", {}),
        "entries": [
            {
                "merchantName": e.get("merchantName"),
                "totalSpent": e.get("totalSpent"),
                "public": e.get("public"),
                "orderStatus": e.get("orderStatus"),
                "ticker": (e.get("buy") or {}).get("ticker") if e.get("buy") else None,
                "isFallback": e.get("isFallback", False),
            }
            for e in plan.get("entries", [])
        ],
        "approvalTrigger": "🏦"
    }))
    return f"{env('SHOP_TO_STOCK_BASE_URL').rstrip('/')}/d/{plan['date']}"


def execute_orders(plan):
    from public_client import submit_fractional_market_buy
    orders = []
    for pick in plan["picks"]:
        try:
            orders.append(submit_fractional_market_buy(pick["ticker"], pick.get("orderDollars", 1)))
        except Exception as e:
            orders.append({"ticker": pick["ticker"], "status": "failed", "message": str(e)})
    plan["orders"] = orders
    order_by_ticker = {o.get('ticker'): o for o in orders}
    for entry in plan.get('entries', []):
        buy = entry.get('buy') or {}
        ticker = buy.get('ticker')
        if ticker and ticker in order_by_ticker:
            status = order_by_ticker[ticker].get('status', 'unknown')
            entry['orderStatus'] = 'placed' if status == 'submitted' else status
            buy['orderStatus'] = entry['orderStatus']
    plan["totals"]["executedInvest"] = round(sum(float(p.get("orderDollars", 1)) for p, o in zip(plan["picks"], orders) if o.get("status") == "submitted"), 2)
    return plan


def print_confirmation(plan):
    print(f"Shop-to-Stock plan for {plan['date']}")
    print(f"Merchant spend: ${plan['totals']['merchantSpend']:.2f}")
    print(f"Planned invest: ${plan['totals']['plannedInvest']:.2f}")
    print("Proposed buys:")
    for pick in plan["picks"]:
        print(f"- {pick['merchantName']} -> {pick['parentCompany']} ({pick['ticker']}) ${pick.get('orderDollars', 1)} [{pick['confidence']}/{pick['resolutionSource']}]")
    if plan["skipped"]:
        print("Skipped / unresolved:")
        for item in plan["skipped"][:12]:
            print(f"- {item['name']}: {item['reason']}")
    print("\nOrders are pending until execution.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target day YYYY-MM-DD; defaults to yesterday")
    parser.add_argument("--publish", action="store_true", help="Publish summary page to Cloudflare KV")
    parser.add_argument("--confirm", action="store_true", help="Execute the proposed orders")
    parser.add_argument("--demo", action="store_true", help="Use built-in demo transactions instead of Teller data")
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    plan = build_plan(target_day(args.date), use_demo=args.demo)
    link = None
    if args.confirm:
        execute_orders(plan)
    if args.publish:
        link = publish_summary(plan)
    if args.json:
        print(json.dumps({"plan": plan, "link": link}, indent=2))
        return
    print_confirmation(plan)
    if plan["orders"]:
        print("\nOrder results:")
        for order in plan["orders"]:
            print(f"- {order['ticker']}: {order.get('status')} {order.get('orderId') or order.get('message','')}")
    if link:
        print(f"\nSummary page: {link}")


if __name__ == "__main__":
    main()
