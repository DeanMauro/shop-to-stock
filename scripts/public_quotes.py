#!/usr/bin/env python3
import os
import subprocess
import sys

try:
    from public_api_sdk import PublicApiClient, PublicApiClientConfiguration, OrderInstrument, InstrumentType
    from public_api_sdk.auth_config import ApiKeyAuthConfig
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'publicdotcom-py==0.1.8'])
    from public_api_sdk import PublicApiClient, PublicApiClientConfiguration, OrderInstrument, InstrumentType
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


def get_equity_quotes(symbols):
    secret = _get_secret()
    account = _get_account()
    if not secret or not account or not symbols:
        return {}
    client = PublicApiClient(ApiKeyAuthConfig(api_secret_key=secret), config=PublicApiClientConfiguration(default_account_number=account))
    try:
        instruments = [OrderInstrument(symbol=s, type=InstrumentType.EQUITY) for s in symbols]
        quotes = client.get_quotes(instruments)
        out = {}
        for q in quotes:
            sym = getattr(getattr(q, 'instrument', None), 'symbol', None)
            last = getattr(q, 'last', None)
            if sym:
                out[sym] = float(last) if last is not None else None
        return out
    finally:
        client.close()
