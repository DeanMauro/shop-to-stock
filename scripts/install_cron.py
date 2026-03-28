#!/usr/bin/env python3
import argparse
import json
import os
import urllib.request


def request(url, token, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gateway-url', default=os.getenv('OPENCLAW_GATEWAY_URL'))
    parser.add_argument('--gateway-token', default=os.getenv('OPENCLAW_GATEWAY_TOKEN'))
    parser.add_argument('--telegram-chat-id', required=True)
    parser.add_argument('--hour', type=int, default=9)
    parser.add_argument('--minute', type=int, default=30)
    parser.add_argument('--tz', default='America/New_York')
    parser.add_argument('--name', default='shop-to-stock daily diary')
    parser.add_argument('--workspace', default=os.getenv('SHOP_TO_STOCK_WORKSPACE', os.getcwd()))
    parser.add_argument('--skill-dir', default=os.getenv('SHOP_TO_STOCK_SKILL_DIR', 'skills/shop-to-stock'))
    args = parser.parse_args()

    if not args.gateway_url or not args.gateway_token:
        raise SystemExit('Missing OPENCLAW_GATEWAY_URL / OPENCLAW_GATEWAY_TOKEN or explicit args')

    workspace = os.path.abspath(args.workspace)
    skill_dir = args.skill_dir
    if not os.path.isabs(skill_dir):
        skill_dir = os.path.join(workspace, skill_dir)

    message = (
        f"Run the shop-to-stock daily diary flow in {workspace} using the skill in {skill_dir}. "
        "Generate and publish today's diary page using real Teller data if available. "
        "If yesterday has no useful merchant transactions, still publish today's diary and use the latest useful available transaction data; say that clearly. "
        "Keep demo mode off. Automatically execute the planned Public.com trades, then republish the diary with updated order statuses and holdings. "
        "After execution, use the exact published diary link/date from the resulting script output or live state, not a guessed fallback date. "
        "Then send the user a concise Telegram message with: (1) the exact diary link, (2) whether older source transaction data was used, (3) key merchants considered, (4) any fallback use, and (5) what trades were submitted or failed. Do not ask for approval."
    )

    job = {
        'name': args.name,
        'schedule': {
            'kind': 'cron',
            'expr': f'{args.minute} {args.hour} * * 1-5',
            'tz': args.tz,
        },
        'payload': {
            'kind': 'agentTurn',
            'message': message,
            'timeoutSeconds': 900,
        },
        'delivery': {
            'mode': 'announce',
            'channel': 'telegram',
            'to': args.telegram_chat_id,
        },
        'sessionTarget': 'isolated',
        'enabled': True,
    }
    out = request(args.gateway_url.rstrip('/') + '/cron/add', args.gateway_token, {'job': job})
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
