#!/usr/bin/env python3
import os
import subprocess
import sys
import uuid
from decimal import Decimal

try:
    from public_api_sdk import (
        PublicApiClient,
        PublicApiClientConfiguration,
        OrderRequest,
        OrderInstrument,
        InstrumentType,
        OrderSide,
        OrderType,
        OrderExpirationRequest,
        TimeInForce,
        EquityMarketSession,
    )
    from public_api_sdk.auth_config import ApiKeyAuthConfig
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.8"])
    from public_api_sdk import (
        PublicApiClient,
        PublicApiClientConfiguration,
        OrderRequest,
        OrderInstrument,
        InstrumentType,
        OrderSide,
        OrderType,
        OrderExpirationRequest,
        TimeInForce,
        EquityMarketSession,
    )
    from public_api_sdk.auth_config import ApiKeyAuthConfig


def get_public_secret():
    secret_file = os.path.expanduser("~/.openclaw/workspace/.secrets/public_com_secret.txt")
    if os.path.exists(secret_file):
        with open(secret_file, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value:
                return value
    return os.getenv("PUBLIC_COM_SECRET")


def get_public_account_id():
    acct_file = os.path.expanduser("~/.openclaw/workspace/.secrets/public_com_account.txt")
    if os.path.exists(acct_file):
        with open(acct_file, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value:
                return value
    return os.getenv("PUBLIC_COM_ACCOUNT_ID")


def create_client(account_id=None):
    secret = get_public_secret()
    acct = account_id or get_public_account_id()
    if not secret:
        raise RuntimeError("PUBLIC_COM_SECRET is not set")
    if not acct:
        raise RuntimeError("PUBLIC_COM_ACCOUNT_ID is not set")
    client = PublicApiClient(
        ApiKeyAuthConfig(api_secret_key=secret),
        config=PublicApiClientConfiguration(default_account_number=acct),
    )
    return client, acct


def submit_fractional_market_buy(symbol, dollars=1, account_id=None, session="CORE", time_in_force="DAY"):
    client, acct = create_client(account_id)
    try:
        order = OrderRequest(
            order_id=str(uuid.uuid4()),
            instrument=OrderInstrument(symbol=symbol, type=InstrumentType.EQUITY),
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount=Decimal(str(dollars)),
            expiration=OrderExpirationRequest(time_in_force=TimeInForce.DAY if time_in_force == "DAY" else TimeInForce.DAY),
            equity_market_session=EquityMarketSession.CORE if session == "CORE" else EquityMarketSession.EXTENDED,
        )
        response = client.place_order(order)
        return {
            "accountId": acct,
            "ticker": symbol,
            "status": "submitted",
            "orderId": getattr(response, "order_id", None),
            "raw": str(response),
        }
    finally:
        client.close()
