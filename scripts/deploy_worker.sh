#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKER_DIR="$DIR/assets/worker"

: "${CLOUDFLARE_ACCOUNT_ID:?missing CLOUDFLARE_ACCOUNT_ID}"
: "${CLOUDFLARE_API_TOKEN:?missing CLOUDFLARE_API_TOKEN}"
: "${CLOUDFLARE_KV_NAMESPACE_ID:?missing CLOUDFLARE_KV_NAMESPACE_ID}"
: "${TELLER_APPLICATION_ID:?missing TELLER_APPLICATION_ID}"

TMP="$WORKER_DIR/wrangler.generated.jsonc"
: "${SHOP_TO_STOCK_ADMIN_SECRET:?missing SHOP_TO_STOCK_ADMIN_SECRET}"
: "${LOGO_DEV_TOKEN:=}"
: "${PUBLIC_COM_ACCOUNT_ID:=}"

sed \
  -e "s/__SET_KV_NAMESPACE_ID__/${CLOUDFLARE_KV_NAMESPACE_ID}/g" \
  -e "s/__SET_TELLER_APPLICATION_ID__/${TELLER_APPLICATION_ID}/g" \
  -e "s/__SET_ADMIN_SECRET__/${SHOP_TO_STOCK_ADMIN_SECRET}/g" \
  -e "s/__SET_LOGO_DEV_TOKEN__/${LOGO_DEV_TOKEN}/g" \
  -e "s/__SET_PUBLIC_COM_ACCOUNT_ID__/${PUBLIC_COM_ACCOUNT_ID}/g" \
  "$WORKER_DIR/wrangler.jsonc" > "$TMP"

export CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_API_TOKEN
npx wrangler deploy "$WORKER_DIR/worker.js" --config "$TMP"

echo "Deployed shop-to-stock worker"
