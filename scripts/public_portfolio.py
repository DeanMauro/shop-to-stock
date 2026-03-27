#!/usr/bin/env python3
import os
import subprocess
import sys

try:
    from public_api_sdk import PublicApiClient, PublicApiClientConfiguration
    from public_api_sdk.auth_config import ApiKeyAuthConfig
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'publicdotcom-py==0.1.8'])
    from public_api_sdk import PublicApiClient, PublicApiClientConfiguration
    from public_api_sdk.auth_config import ApiKeyAuthConfig


def _get_secret():
    p = os.path.expanduser('~/.openclaw/workspace/.secrets/public_com_secret.txt')
    if os.path.exists(p):
        return open(p, 'r', encoding='utf-8').read().strip()
    return os.getenv('PUBLIC_COM_SECRET')


def _get_account():
    p = os.path.expanduser('~/.openclaw/workspace/.secrets/public_com_account.txt')
    if os.path.exists(p):
        return open(p, 'r', encoding='utf-8').read().strip()
    return os.getenv('PUBLIC_COM_ACCOUNT_ID')


def get_portfolio_snapshot(limit=8):
    secret = _get_secret()
    account = _get_account()
    if not secret or not account:
        return {"positions": [], "buyingPower": None, "accountNumber": account}
    client = PublicApiClient(ApiKeyAuthConfig(api_secret_key=secret), config=PublicApiClientConfiguration(default_account_number=account))
    try:
        portfolio = client.get_portfolio()
        positions = []
        for pos in getattr(portfolio, 'positions', []) or []:
            inst = getattr(pos, 'instrument', None)
            if not inst or getattr(inst, 'type', None).value != 'EQUITY':
                continue
            positions.append({
                'symbol': getattr(inst, 'symbol', None),
                'name': getattr(inst, 'name', None),
                'quantity': float(getattr(pos, 'quantity', 0) or 0),
                'currentValue': float(getattr(pos, 'current_value', 0) or 0),
                'lastPrice': float(getattr(getattr(pos, 'last_price', None), 'last_price', 0) or 0),
                'percentOfPortfolio': float(getattr(pos, 'percent_of_portfolio', 0) or 0),
            })
        positions.sort(key=lambda p: p['currentValue'], reverse=True)
        bp = getattr(portfolio, 'buying_power', None)
        return {
            'positions': positions[:limit],
            'buyingPower': float(getattr(bp, 'buying_power', 0) or 0) if bp else None,
            'accountNumber': account,
        }
    finally:
        client.close()
