# Configuration

## Required environment variables

### Teller
- `TELLER_CERT_FILE`
- `TELLER_KEY_FILE`
- `TELLER_ACCESS_TOKEN` (required after connect is completed)
- `TELLER_APPLICATION_ID`

Teller uses mutual TLS plus an access token. The skill assumes the cert/key files already exist on disk and are referenced by path. Before connect is completed, the Worker handles Teller Connect and stores a retrieval nonce so OpenClaw can pull and persist the fresh `TELLER_ACCESS_TOKEN`.

### Public.com
- `PUBLIC_COM_SECRET`
- `PUBLIC_COM_ACCOUNT_ID`

The skill uses the Public.com Python SDK approach from the installed public.com skill and also honors secure files under `~/.openclaw/workspace/.secrets/`.

### Cloudflare
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_KV_NAMESPACE_ID`
- `SHOP_TO_STOCK_BASE_URL`
- `SHOP_TO_STOCK_ADMIN_SECRET`

### Optional resolver input
- `BRAVE_API_KEY` — enables a second-pass web-search heuristic for merchant -> parent ticker resolution.
- `LOGO_DEV_TOKEN` — required if you want ticker logos to render on the hosted summary page.

### Telegram / Cron delivery
- `TELEGRAM_CHAT_ID` (recommended for deterministic cron setup)
- `OPENCLAW_GATEWAY_URL` (needed by `scripts/install_cron.py` unless passed explicitly)
- `OPENCLAW_GATEWAY_TOKEN` (needed by `scripts/install_cron.py` unless passed explicitly)

## Daily execution model

1. Build a diary for the requested/current day.
   - Recommended production cron time: 9:30 AM America/New_York (market open)
2. Attempt to use prior-day transactions first.
3. If the requested day has no useful merchant activity, fall back to the latest useful available transaction date.
4. Keep the published diary on the requested/current day even when older source data is used.
5. Filter to merchant spend.
6. Aggregate by normalized merchant.
7. Resolve parent company + ticker.
8. Select up to 5 unique names.
9. Produce a review payload.
10. On confirmation, place fractional Public.com buys.
11. Store summary JSON in KV.
12. Store latest pending diary metadata in KV.
13. Link to `/d/YYYY-MM-DD` on the worker.
14. Send the link and execution summary over the configured chat channel (Telegram supported explicitly via `delivery.to`).

## Suggested KV shape

Keys:
- `summary:YYYY-MM-DD`
- `status:connected`
- `status:data-insight`
- `status:latest-pending-diary`
- `pending-token:<nonce>`
- `debug:last-connect-attempt`
- optional debug/test keys as needed during KV diagnostics

Primary summary value shape:
```json
{
  "date": "2026-03-27",
  "sourceTransactionDate": "2026-03-13",
  "usedLatestAvailableTransactions": true,
  "totals": {
    "merchantSpend": 26.63,
    "plannedInvest": 5,
    "executedInvest": 0
  },
  "merchants": [],
  "skipped": [],
  "picks": [],
  "orders": [],
  "generatedAt": "2026-03-27T21:00:00Z",
  "confirmationRequired": true
}
```

## Execution flow

For unattended operation, the default behavior is:

1. Build and publish the diary.
2. Execute the planned trades automatically.
3. Republish the diary with updated statuses.
4. Send the user the resulting diary link and trade summary.

Use `--confirm --publish` for the automated daily run.

Important implementation note: the Public SDK expects a real string `order_id` on `OrderRequest`. Generate a UUID (or equivalent unique string) for each submitted order; do not pass `None`.

If submission succeeds but republishing fails, reconcile the diary/UI state by writing the updated summary payload and latest state back to KV directly instead of resubmitting the trade.

Optional pending-diary metadata can still be stored in KV, but approval replies are no longer required for the default cron path.

## Demo mode

`shop_to_stock.py` supports an explicit `--demo` flag that injects sample merchant data for showcase/testing flows.

The built-in sample includes:
- Amazon
- Uber
- Starbucks
- Live Nation
- Alibaba
- Wegmans
- Clifton Bagels
- J&R Sports Bar
- Da Vinci Bakery

Keep demo mode opt-in. Do not enable it by default for public users.
