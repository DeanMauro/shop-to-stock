# shop-to-stock

Turn your shopping habits into a tiny investing ritual.

**Shop-to-Stock** connects your bank with **Teller**, maps your recent merchant activity to public companies when possible, places tiny buys through **Public.com**, and publishes a gorgeous daily diary page so you can see what happened.

The vibe is simple:
- shopped at a public company? buy a little of it
- not enough good public matches? fall back to the trusty **S&P 500**
- get a daily update in chat before the market opens
- watch your spending slowly turn into ownership

It’s part investing experiment, part product demo, part delight machine.

---

## What this does

At a high level, Shop-to-Stock:

1. Connects your bank account through Teller
2. Pulls merchant transactions
3. Cleans up merchant names
4. Resolves them to public parent-company tickers when it can
5. Builds a daily investment diary
6. Places tiny Public.com buys automatically
7. Publishes a hosted diary page with statuses and holdings
8. Sends you the result in Telegram

If there aren’t enough usable public-company matches, it falls back to **SPY** so the daily ritual still happens.

---

## What you’ll need

This project is designed to run through **OpenClaw** with a deployed **Cloudflare Worker**, **Teller** for bank connectivity, and **Public.com** for trading.

### Core requirements

- **OpenClaw**
  - Docs: <https://docs.openclaw.ai>
  - Source: <https://github.com/openclaw/openclaw>
- **Cloudflare account** with Workers + KV access
  - Cloudflare Workers: <https://developers.cloudflare.com/workers/>
  - Cloudflare KV: <https://developers.cloudflare.com/kv/>
- **Teller** account and Teller Connect app
  - Teller docs: <https://teller.io/docs/>
  - Teller Connect: <https://teller.io/docs/connect/>
- **Public.com API access**
  - Public developer docs: <https://public.com/api>
- Optional but recommended:
  - **Brave Search API** for better merchant → ticker fallback resolution: <https://brave.com/search/api/>
  - **logo.dev** for ticker logos in the diary UI: <https://logo.dev>

### Local tools

- Python 3
- Node / npm
- `wrangler` (installed automatically via `npx wrangler deploy` in the deploy script)
- a machine running OpenClaw where you can store local secrets securely

---

## Required configuration

Shop-to-Stock needs the following environment variables or equivalent secure local configuration.

### Teller

- `TELLER_CERT_FILE`
- `TELLER_KEY_FILE`
- `TELLER_APPLICATION_ID`
- `TELLER_ACCESS_TOKEN` *(added after bank connect is completed)*

How to get them:
- Create a Teller app / get your application id:
  <https://teller.io/docs/connect/>
- Generate/download your Teller certificates for mTLS:
  <https://teller.io/docs/api#mutual-tls>
- `TELLER_ACCESS_TOKEN` is created after the user completes Teller Connect in the hosted worker flow

### Public.com

- `PUBLIC_COM_SECRET`
- `PUBLIC_COM_ACCOUNT_ID`

How to get them:
- Public API docs: <https://public.com/api>
- You’ll need API credentials and the target brokerage account number you want trades placed in

### Cloudflare

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_KV_NAMESPACE_ID`
- `SHOP_TO_STOCK_BASE_URL`
- `SHOP_TO_STOCK_ADMIN_SECRET`

How to get them:
- Cloudflare account id: dashboard overview
- API token for Workers/KV operations:
  <https://developers.cloudflare.com/fundamentals/api/get-started/create-token/>
- Create a KV namespace:
  <https://developers.cloudflare.com/kv/get-started/>
- `SHOP_TO_STOCK_BASE_URL` is your deployed worker URL
- `SHOP_TO_STOCK_ADMIN_SECRET` can be any strong random secret used to retrieve pending Teller tokens and protected debug state

### Telegram / cron delivery

- `TELEGRAM_CHAT_ID`
- `OPENCLAW_GATEWAY_URL`
- `OPENCLAW_GATEWAY_TOKEN`

How to get them:
- `TELEGRAM_CHAT_ID` is the Telegram chat target for delivery
- Gateway URL/token depend on your OpenClaw deployment and cron setup

### Optional but useful

- `BRAVE_API_KEY`
- `LOGO_DEV_TOKEN`

---

## OpenClaw setup guide

This is the cleanest way to get Shop-to-Stock running inside OpenClaw.

### 1. Install the skill

Add the skill into your OpenClaw workspace or install the packaged `.skill` artifact.

If you’re using the skill folder directly, place it under your skills directory as:

```text
skills/shop-to-stock
```

### 2. Add your secrets / env vars

Populate your secure config with the required values above.

A common local pattern is a shell file like:

```bash
export TELLER_CERT_FILE=/path/to/certificate.pem
export TELLER_KEY_FILE=/path/to/private_key.pem
export PUBLIC_COM_SECRET=...
export PUBLIC_COM_ACCOUNT_ID=...
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_KV_NAMESPACE_ID=...
export SHOP_TO_STOCK_BASE_URL=https://your-worker.workers.dev
export SHOP_TO_STOCK_ADMIN_SECRET=...
export TELLER_APPLICATION_ID=...
export TELEGRAM_CHAT_ID=...
export OPENCLAW_GATEWAY_URL=...
export OPENCLAW_GATEWAY_TOKEN=...
```

### 3. Validate setup

Run:

```bash
python3 scripts/validate_setup.py
```

This checks whether the required env vars and local Teller cert/key files are present.

### 4. Deploy the worker

Run:

```bash
bash scripts/deploy_worker.sh
```

That publishes the hosted UI / diary app to Cloudflare Workers.

### 5. Connect the bank account

Open:

```text
https://<your-worker-host>/connect
```

Complete the Teller Connect flow.

When it succeeds, the page will show a **nonce**.

### 6. Retrieve and save the Teller access token

Run:

```bash
python3 scripts/retrieve_teller_token.py --nonce <nonce>
```

This pulls the fresh Teller access token from the worker and updates your local env file.

### 7. Test a diary run manually

To generate and publish a diary without demo mode:

```bash
python3 scripts/shop_to_stock.py --publish --json
```

To place trades and republish the diary:

```bash
python3 scripts/shop_to_stock.py --confirm --publish --json
```

### 8. Install the daily cron

To create the Telegram-delivered pre-market job:

```bash
python3 scripts/install_cron.py --telegram-chat-id <chat-id>
```

That cron is designed to:
- generate today’s diary
- use the latest useful available transaction data if needed
- place the planned trades automatically
- republish the diary with updated statuses
- message you the final result in Telegram

---

## How it works

This section is a good place for screenshots and annotated examples.

### Step 1 — Bank connection

_Add screenshot of the hosted `/connect` page here._

The worker hosts a Teller Connect onboarding page. Once the user completes bank linking, the worker stores the pending Teller token and connection metadata.

### Step 2 — Daily diary generation

_Add screenshot of the diary homepage or date picker here._

Each day, Shop-to-Stock builds a diary page for the current run date.

Important detail:
- if yesterday has no useful merchant transactions,
- the diary still publishes for **today**,
- but transparently notes that it used the latest useful available transaction date.

### Step 3 — Merchant matching

_Add screenshot of diary line items here._

Merchant names are cleaned up and matched to public parent companies when possible.

Examples:
- Starbucks → `SBUX`
- Uber → `UBER`
- Live Nation → `LYV`
- Whole Foods → `AMZN`

If no strong public-company match exists, that merchant remains visible in the diary but does not generate a direct stock buy.

### Step 4 — Fallback behavior

_Add screenshot of fallback row here._

If there aren’t enough public matches, Shop-to-Stock falls back to a single **SPY** row with the full fallback amount.

That means the investing loop still happens even on boring days.

### Step 5 — Holdings + status updates

_Add screenshot of holdings section here._

After trades execute, the worker republishes the diary and updates holdings so the hosted page reflects:
- what was submitted
- what was skipped
- current holdings snapshot
- buying power in the Public account

---

## Notes and gotchas

- **Public SDK order ids matter.**
  The Public order request must include a real string `order_id`. Passing `None` will fail validation.

- **Trade submit and republish are separate concerns.**
  If an order succeeds but diary republish fails, reconcile the UI by updating the summary payload in KV rather than resubmitting the trade.

- **Teller data can lag.**
  You may see today’s diary built from older source transaction data if no newer useful merchant transactions are available yet.

- **You may buy the same company on multiple days in a row.**
  That is expected and acceptable in this design.

- **This is real money.**
  Even though the default buy sizes are tiny, auto-trading should still be treated with care.

---

## Repo structure

```text
SKILL.md
assets/worker/
references/
scripts/
```

### Important scripts

- `scripts/validate_setup.py`
- `scripts/retrieve_teller_token.py`
- `scripts/install_cron.py`
- `scripts/shop_to_stock.py`
- `scripts/deploy_worker.sh`

---

## License

See the repository license file.
