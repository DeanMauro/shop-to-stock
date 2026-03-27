---
name: shop-to-stock
description: Build, deploy, and operate a reusable finance workflow that turns prior-day merchant spend into small Public.com stock purchases. Use when creating, configuring, improving, or running a “shop to stock” automation with Teller bank linking, a Cloudflare Worker diary UI, daily diary generation, automatic Public trade execution, cron scheduling before market open, or post-trade diary/holdings updates.
---

# Shop To Stock

Use this skill to create or operate a workflow that:

1. Connects a bank account with Teller Connect.
2. Pulls prior-day merchant transactions from Teller.
3. Normalizes merchants and resolves public parent-company tickers.
4. Builds a Public.com buy plan.
5. Executes Public.com trades automatically when configured to do so.
6. Publishes a hosted diary page to Cloudflare Workers + KV.
7. Notifies the user with the diary link and execution results.
8. Updates diary/order state after execution.

## Files to read when needed

- `references/configuration.md` — env vars, KV shape, execution model
- `references/heuristics.md` — merchant cleanup and ticker-resolution rules
- `scripts/validate_setup.py` — deterministic setup validator for from-scratch installs
- `scripts/retrieve_teller_token.py` — pulls the Teller token from a connect nonce and updates local env config
- `scripts/install_cron.py` — deterministic daily cron installer for Telegram delivery
- `scripts/shop_to_stock.py` — core planner / publisher / executor
- `scripts/ticker_resolver.py` — deterministic and search-backed ticker resolution
- `scripts/public_client.py` — Public.com trade helper
- `scripts/public_portfolio.py` — holdings / buying-power snapshot helper
- `scripts/deploy_worker.sh` — Worker deployment script
- `assets/worker/worker.js` — Worker UI and nonce retrieval flow

## Workflow

### 1. Confirm configuration

Read `references/configuration.md`.

For from-scratch installs, run this first:

```bash
python3 scripts/validate_setup.py
```

Require these secure values:

- `TELLER_CERT_FILE`
- `TELLER_KEY_FILE`
- `PUBLIC_COM_SECRET`
- `PUBLIC_COM_ACCOUNT_ID`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_KV_NAMESPACE_ID`
- `SHOP_TO_STOCK_BASE_URL`
- `SHOP_TO_STOCK_ADMIN_SECRET`
- `TELLER_APPLICATION_ID`

Optional but useful:

- `TELLER_ACCESS_TOKEN` — present after the bank is already connected
- `BRAVE_API_KEY`
- `LOGO_DEV_TOKEN`

If Teller is not connected yet, do not block on `TELLER_ACCESS_TOKEN`; complete the Worker connect flow first.

### 2. Deploy the Worker and connect the bank

Deploy or refresh the Worker:

```bash
scripts/deploy_worker.sh
```

Then send the user to:

```text
https://<worker-host>/connect
```

The user completes Teller Connect in-browser. On success, the Worker stores:

- `status:connected`
- `pending-token:<nonce>`
- debug status for the last connect attempt

Ask the user for the retrieval nonce shown on the page.

Fetch the pending token from the Worker using the admin secret:

```text
GET /pending-token/<nonce>?secret=<SHOP_TO_STOCK_ADMIN_SECRET>
```

Update local secure config so `TELLER_ACCESS_TOKEN` uses the fresh access token before running the pipeline.

Prefer the deterministic helper:

```bash
python3 scripts/retrieve_teller_token.py --nonce <nonce>
```

Use the protected Worker debug endpoint when troubleshooting connect/save issues:

```text
GET /debug/status?secret=<SHOP_TO_STOCK_ADMIN_SECRET>
```

### 3. Build and publish a diary page

Build the plan first without placing trades:

```bash
python3 scripts/shop_to_stock.py --json
```

Publish the diary page:

```bash
python3 scripts/shop_to_stock.py --publish --json
```

For demos or showcases, use explicit demo mode:

```bash
python3 scripts/shop_to_stock.py --demo --publish --json
```

Current behavior worth preserving:

- prefer real merchant / counterparty / description fields over Teller `processing_status`
- if the requested diary day has no useful merchant transactions, keep publishing the diary for the requested/current day but populate it from the latest useful available transaction date
- include `sourceTransactionDate` and `usedLatestAvailableTransactions` in the payload when that fallback happens
- keep real merchant rows visible even when fallback is needed
- collapse fallback into one SPY row with the full dollar amount and estimated shares
- use the fun fallback explanation when fallback is active, plus note when older source data is being used for today’s diary
- keep the hosted homepage updated with connection state, latest transaction date, account summary, exact Public account number, holdings, and buying power
- keep the diary mobile-friendly: condense the top stats into a single compact block on mobile, stack line items cleanly, show per-field labels on small screens, and leave breathing room between mobile labels and their content

### 4. Execute trades and publish the diary

When auto-trading is desired, run:

```bash
python3 scripts/shop_to_stock.py --confirm --publish --json
```

That should:

- submit fractional buys through Public.com
- generate a valid client `order_id` for each `OrderRequest` (do not pass `None`)
- update entry/order statuses
- republish the diary payload to KV
- leave the hosted page showing the updated status and holdings snapshot

After execution, send the updated diary link and summarize filled/submitted/failed results.

If trade submission succeeds but the combined script path fails during republish, treat those as separate concerns: preserve the successful order result, then reconcile the live diary by writing the updated summary/order state back to KV directly.

### 5. Automate the daily loop with cron

Create a daily cron job that runs before market open in the user’s timezone.

Recommended cron behavior:

1. Generate that day’s diary.
2. If prior-day data is empty, still publish today’s diary using the latest useful available transactions.
3. Execute the planned Public.com trades automatically.
4. Republish the diary with updated order statuses.
5. Announce the diary link directly to the user with what was bought and any fallback use.

Use a cron `agentTurn` job for the daily diary-generation task, not a `systemEvent` reminder.

Prefer the deterministic helper for setup:

```bash
python3 scripts/install_cron.py --telegram-chat-id <chat-id>
```

Recommended delivery shape:

- `sessionTarget: "isolated"`
- `delivery.mode: "announce"`
- set `delivery.channel` explicitly when multiple channels exist
- set `delivery.to` explicitly for Telegram delivery (chat id required)

The cron run should be fully self-contained: it generates the diary, places the trades, republishes the diary, and then announces the result to the user.

## Reality check on the current product loop

The intended loop is:

1. User installs skill and provides secure config.
2. OpenClaw deploys the Worker and gives the user the `/connect` bank-link URL.
3. User connects the bank and sends back the nonce.
4. OpenClaw retrieves the fresh Teller token and stores it locally.
5. OpenClaw generates a diary page for today.
6. If the freshest useful transactions are older than yesterday, today’s diary still publishes on today’s date and notes the older source transaction date.
7. OpenClaw executes the planned Public.com trades automatically.
8. OpenClaw republishes the diary with updated statuses and holdings.
9. OpenClaw sends the resulting diary link and execution summary to the user.
10. A daily cron job keeps doing this before market open over the configured delivery channel.

## Operating notes

- Favor deterministic mappings before search heuristics.
- Skip weak ticker matches.
- Keep secrets in secure config only.
- Default to confirmation mode for public distribution.
- Prefer truthful UI over overly tidy UI: keep real merchant rows visible even when fallback is used.
- Use the Worker debug endpoint when bank-link state looks wrong.
