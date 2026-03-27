#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def fetch_json(url):
    req = urllib.request.Request(url, headers={'user-agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def update_env_file(path, token):
    p = Path(path)
    text = p.read_text() if p.exists() else ''
    line = f'export TELLER_ACCESS_TOKEN={token}'
    if 'export TELLER_ACCESS_TOKEN=' in text:
        text = re.sub(r'^export TELLER_ACCESS_TOKEN=.*$', line, text, flags=re.M)
    else:
        if text and not text.endswith('\n'):
            text += '\n'
        text += line + '\n'
    p.write_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--base-url', default=os.getenv('SHOP_TO_STOCK_BASE_URL'))
    parser.add_argument('--admin-secret', default=os.getenv('SHOP_TO_STOCK_ADMIN_SECRET'))
    parser.add_argument('--env-file', default=os.path.expanduser('~/.openclaw/workspace/.secrets/shop_to_stock_env.sh'))
    args = parser.parse_args()

    if not args.base_url:
        raise SystemExit('Missing --base-url or SHOP_TO_STOCK_BASE_URL')
    if not args.admin_secret:
        raise SystemExit('Missing --admin-secret or SHOP_TO_STOCK_ADMIN_SECRET')

    url = f"{args.base_url.rstrip('/')}/pending-token/{args.nonce}?secret={args.admin_secret}"
    payload = fetch_json(url)
    token = payload.get('accessToken')
    if not token:
        raise SystemExit('No accessToken returned from pending-token endpoint')
    update_env_file(args.env_file, token)
    print(json.dumps({
        'ok': True,
        'nonce': args.nonce,
        'institution': ((payload.get('enrollment') or {}).get('enrollment') or {}).get('institution', {}).get('name'),
        'envFile': args.env_file,
    }, indent=2))


if __name__ == '__main__':
    main()
