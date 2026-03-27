# Merchant and ticker heuristics

## Merchant filtering

Treat these as likely exclusions unless there is strong contrary evidence:
- ATM
- CASH
- WITHDRAWAL
- TRANSFER
- ACH
- PAYMENT
- PAYROLL
- VENMO
- ZELLE
- CASH APP
- APPLE CASH
- FEE
- INTEREST
- ADJUSTMENT
- REVERSAL

## Merchant normalization

Apply these steps in order:

1. Uppercase and trim.
2. Remove obvious processor prefixes/suffixes and bank noise:
   - `SQ *`
   - `PAYPAL *`
   - `TST*`
   - `POS `
   - trailing city/state fragments when clearly not part of the brand
3. Remove order IDs, reference fragments, duplicate whitespace, and punctuation noise.
4. Collapse known aliases to a canonical merchant.
5. Prefer the underlying merchant over the payment processor when recognizable.

Examples:
- `AMZN Mktp US*AB12` -> `Amazon`
- `SQ *JOES COFFEE` -> `Joe's Coffee`
- `PAYPAL *UBER` -> `Uber`
- `APPLE.COM/BILL` -> `Apple`
- `WHOLEFDS BKLYN` -> `Whole Foods`

## Ticker resolution order

1. Use built-in brand-to-parent map.
2. Use merchant name plus web search heuristic.
3. Verify that the company is publicly traded.
4. Prefer parent company over brand when the brand is not independently public.
5. Prefer US major-exchange common stock.
6. Skip low-confidence results.

## Confidence rules

High confidence examples:
- Whole Foods -> Amazon (`AMZN`)
- Instagram -> Meta (`META`)
- Google Store -> Alphabet (`GOOGL`)
- Starbucks -> Starbucks (`SBUX`)
- Uber -> Uber (`UBER`)
- Alibaba -> Alibaba (`BABA`)
- Live Nation -> Live Nation Entertainment (`LYV`)

Low confidence examples:
- generic local merchants
- private restaurant groups
- ambiguous abbreviations without strong web corroboration

When confidence is low, skip.
