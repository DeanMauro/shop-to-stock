# shop-to-stock

Turn your shopping habits into a tiny investing ritual.

**Shop-to-Stock** connects your bank with **Teller**, maps your recent merchant activity to public companies where possible, buys $1 of each company's stock through **Public.com**, and sends you a  daily summary so you can see your wealth grow in real time.

The idea is simple:
You're doing research and supporting a vendor every time you shop. Why not be an owner too?
(Oh and if you don't make a lot of purchases, don't worry. We'll toss $5 in the trusty **S&P 500** instead)

## Table of contents

- [What this does](#what-this-does)
- [What you'll need](#what-youll-need)
- [Setup](#setup)
- [OpenClaw setup guide](#openclaw-setup-guide)
- [How it works](#how-it-works)
- [Notes and gotchas](#notes-and-gotchas)
- [Repo structure](#repo-structure)
- [License](#license)

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

## Setup

Shop-to-Stock needs the following environment variables or equivalent secure local configuration. All services used are free!

### Teller
* Connects to your bank account to grab daily transactions *

- `TELLER_CERT_FILE`
- `TELLER_KEY_FILE`
- `TELLER_APPLICATION_ID`
- `TELLER_ACCESS_TOKEN` *(added after bank connect is completed)*

How to get them:
- Create a Teller app / get your application id:
  <https://teller.io>
  
  <img width="540" height="200" alt="Screenshot 2026-03-27 at 2 04 43 PM" src="https://github.com/user-attachments/assets/889957d5-bfcb-4f93-aa48-d38b0edae442" />

- Generate/download your Teller certificates for mTLS:

  <img width="554" height="337" alt="Screenshot 2026-03-27 at 2 07 56 PM" src="https://github.com/user-attachments/assets/d1f2ae3b-ec4b-46c9-a27d-c4712bf36fa2" />

- Don't worry about `TELLER_ACCESS_TOKEN`. It gets created automatically when you connect your account to OpenClaw.

### Public.com
* An awesome brokerage that lets your agent place trades *

- `PUBLIC_COM_SECRET`
- `PUBLIC_COM_ACCOUNT_ID`

How to get them:
- Create an API key on public.com: <[https://public.com/api](https://public.com/settings/v2/api)>

<img width="259" height="225" alt="Screenshot 2026-03-27 at 2 11 07 PM" src="https://github.com/user-attachments/assets/55845bb9-2824-431b-9d72-5df70dc47dba" />

- Grab your account ID from the hamburger menu

<img width="390" height="200" alt="Screenshot 2026-03-27 at 2 16 09 PM" src="https://github.com/user-attachments/assets/5fb4160f-ef16-4afa-8e4e-6a5251d25cfc" />


### Cloudflare
* Hosts UIs for when we need to go beyond the chat interface *

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_KV_NAMESPACE_ID`

These are the Cloudflare values **you** provide.

How to get them:
- Cloudflare account id: dashboard overview
  
<img width="428" height="178" alt="Screenshot 2026-03-27 at 2 24 45 PM" src="https://github.com/user-attachments/assets/bb14dfba-06f0-4ca1-957d-685eb7cffdec" />

- API token for Workers/KV operations:
  <https://dash.cloudflare.com/profile/api-tokens>
  
<img width="688" height="57" alt="Screenshot 2026-03-27 at 2 22 36 PM" src="https://github.com/user-attachments/assets/9ccc1234-391d-46bc-8766-9ae7c986eab2" />

- Create a KV namespace:
  <https://developers.cloudflare.com/kv/get-started/>

### Telegram / cron delivery

- `TELEGRAM_CHAT_ID`

How to get it:
- `TELEGRAM_CHAT_ID` is the Telegram chat target for delivery

### What setup creates for you

You do **not** need to manually provide these ahead of time:

- `SHOP_TO_STOCK_BASE_URL`
  - created once the worker is deployed
- `SHOP_TO_STOCK_ADMIN_SECRET`
  - should be generated during setup
- `TELLER_ACCESS_TOKEN`
  - created automatically after the bank connect flow is completed

### What OpenClaw should already provide

These are runtime/operator values, not normal end-user setup inputs:

- `OPENCLAW_GATEWAY_URL`
- `OPENCLAW_GATEWAY_TOKEN`

If you are running inside a normal OpenClaw environment, you usually should not need to manually hunt these down just to use the skill.

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
export TELLER_APPLICATION_ID=...
export TELEGRAM_CHAT_ID=...
```

Then, during setup:
- worker deployment gives you `SHOP_TO_STOCK_BASE_URL`
- setup generates `SHOP_TO_STOCK_ADMIN_SECRET`
- bank connect creates `TELLER_ACCESS_TOKEN`
- OpenClaw runtime should provide `OPENCLAW_GATEWAY_URL` / `OPENCLAW_GATEWAY_TOKEN` for cron installation

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
