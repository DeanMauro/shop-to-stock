# shop-to-stock

Turn your shopping habits into a tiny investing ritual.

**Shop-to-Stock** connects your bank with **Teller**, maps your recent merchant activity to public companies where possible, buys $1 of each company's stock through **Public.com**, and sends you a  daily summary so you can see your wealth grow in real time.

The idea is simple:
You're doing research and supporting a vendor every time you shop. Why not be an owner too?
(Oh and if you don't make a lot of purchases, don't worry. We'll toss $5 in the trusty **S&P 500** instead)

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

## How it works

Once OpenClaw has everything set up, it will guide you through the following:

### Step 0 — The UI

Once it creates a Cloudflare Worker and builds the "Shop to Stock" UI, your claw will send you a link to it. Chat is great but for some things, you need to be able to point and click or see things visually that can't be captured in text. It looks something like this:

<img width="600" height="500" alt="Screenshot 2026-03-27 at 2 48 00 PM" src="https://github.com/user-attachments/assets/d3a52e71-2a6f-4544-a36a-cc77a8832784" />

### Step 1 — Bank connection

First things first. We need to let OpenClaw see our bank transactions. It should prompt you to head to the connect page and use Teller to hook up your bank account. You can choose as many or few of your accounts/cards as you like. I use my credit card for everything so I just went with that.

<img width="240" height="400" alt="Screenshot 2026-03-27 at 2 43 18 PM" src="https://github.com/user-attachments/assets/7d1f2e6e-0cd0-41b5-a86a-a9eaa053b97e" />

<img width="240" height="400" alt="Screenshot 2026-03-27 at 2 43 27 PM" src="https://github.com/user-attachments/assets/ca3fe110-1124-4ff9-85c8-b816dbd7f1f3" />


### Step 2 — Daily Summary

<img width="762" height="600" alt="Screenshot 2026-03-27 at 2 58 32 PM" src="https://github.com/user-attachments/assets/6f81fa63-52e4-491d-bb32-182c408deeaf" />

Each day, OpenClaw adds a page to our investing diary sharing what purchases it found and which stocks it bought in response.

Important detail:
- If you made no purchases, OpenClaw will use those from the last day that had purchases.
- If you made purchases but none were from public companies, OpenClaw will buy SPY.

### Step 3 — Buy Some Stocks!

OpenClaw will then purchase $1 of each company's stock on Public, update your current holdings and buying power on the homepage.

### Step 4 — Notification

Once your investments have been placed, OpenClaw will message you on Telegram with a link to the summary for that day so you can follow your wealth-building journey in real-time!

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

Shop-to-Stock needs the following environment variables or equivalent secure local configuration. I know, there's a lot but all these services are free and makes the experience great!

### Teller
*Connects to your bank account to grab daily transactions*

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
*An awesome brokerage that lets your agent place trades*

- `PUBLIC_COM_SECRET`
- `PUBLIC_COM_ACCOUNT_ID`

How to get them:
- Create an API key on public.com: <[https://public.com/api](https://public.com/settings/v2/api)>

<img width="259" height="225" alt="Screenshot 2026-03-27 at 2 11 07 PM" src="https://github.com/user-attachments/assets/55845bb9-2824-431b-9d72-5df70dc47dba" />

- Grab your account ID from the hamburger menu

<img width="390" height="200" alt="Screenshot 2026-03-27 at 2 16 09 PM" src="https://github.com/user-attachments/assets/5fb4160f-ef16-4afa-8e4e-6a5251d25cfc" />


### Cloudflare
*Hosts UIs for when we need to go beyond the chat interface*

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

### Logo.dev
*Provides logos for each company you invest in*

- `LOGO_DEV_TOKEN`

How to get it:
- Create a FREE account [here](https://www.logo.dev)

### Telegram / cron delivery
*Lets OpenClaw send you updates each day even if you're on the go!*

- `TELEGRAM_CHAT_ID`

How to get it:
- Follow the guide to setup Telegram in OpenClaw [here](https://docs.openclaw.ai/channels/telegram), then get the ID of the chat it creates.

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

- `BRAVE_API_KEY` or whichever [search provider you use in OpenClaw](https://docs.openclaw.ai/tools/brave-search#brave-search)

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

### 3. Tell OpenClaw to set it up

OpenClaw has the scripts to take it from here.

---


## Notes and gotchas

- **Teller data can lag.**
  You may see today’s diary built from older source transaction data if no newer useful merchant transactions are available yet.

- **You may buy the same company on multiple days in a row.**
  That is expected and acceptable in this design.

- **This is real money.**
  Even though the default buy sizes are tiny, auto-trading should still be treated with care.

## Disclaimer

The information provided in this repo is for general informational purposes only and is not legal, tax, accounting, or investment advice. Past performance, including hypothetical or backtested results, does not guarantee future results. Trading and investing in any asset class, including equities, options, futures, and digital assets (including crypto), involves substantial risk and may result in losses up to and including the loss of your entire investment. You should not invest or risk money you cannot afford to lose. Online trading is not suitable for all investors. All product and company names and logos are trademarks™ or registered trademarks® of their respective holders, and their use does not imply affiliation with or endorsement by those holders.
