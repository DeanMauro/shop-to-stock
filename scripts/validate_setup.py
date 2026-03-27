#!/usr/bin/env python3
import os
import sys
from pathlib import Path

REQUIRED_ENV = [
    'TELLER_CERT_FILE',
    'TELLER_KEY_FILE',
    'PUBLIC_COM_SECRET',
    'PUBLIC_COM_ACCOUNT_ID',
    'CLOUDFLARE_ACCOUNT_ID',
    'CLOUDFLARE_API_TOKEN',
    'CLOUDFLARE_KV_NAMESPACE_ID',
    'SHOP_TO_STOCK_BASE_URL',
    'SHOP_TO_STOCK_ADMIN_SECRET',
    'TELLER_APPLICATION_ID',
]
OPTIONAL_ENV = [
    'TELLER_ACCESS_TOKEN',
    'BRAVE_API_KEY',
    'LOGO_DEV_TOKEN',
]


def env(name):
    return os.getenv(name)


def check_file(path_value, label):
    p = Path(path_value)
    if not p.exists():
        return f'{label}: missing file at {p}'
    if not p.is_file():
        return f'{label}: expected file but found non-file at {p}'
    return None


def main():
    errors = []
    warnings = []

    for name in REQUIRED_ENV:
        if not env(name):
            errors.append(f'Missing required env var: {name}')

    cert = env('TELLER_CERT_FILE')
    key = env('TELLER_KEY_FILE')
    if cert:
        err = check_file(cert, 'TELLER_CERT_FILE')
        if err:
            errors.append(err)
    if key:
        err = check_file(key, 'TELLER_KEY_FILE')
        if err:
            errors.append(err)

    if not env('TELLER_ACCESS_TOKEN'):
        warnings.append('TELLER_ACCESS_TOKEN is not set yet. That is expected before the user completes Teller Connect.')

    print('Shop-to-Stock setup validation')
    print('==============================')
    if errors:
        print('\nErrors:')
        for item in errors:
            print(f'- {item}')
    if warnings:
        print('\nWarnings:')
        for item in warnings:
            print(f'- {item}')
    print('\nOptional env vars detected:')
    for name in OPTIONAL_ENV:
        status = 'set' if env(name) else 'not set'
        print(f'- {name}: {status}')

    if errors:
        sys.exit(1)
    print('\nValidation passed.')


if __name__ == '__main__':
    main()
