# Invoice

The invoice CSV the accounting system imports for each order.

## Sub-features
- export: one row per cart line with its line amount, then a `TOTAL` row.

## How to get to it (user POV)
- Accounting runs `python3 -m shop.invoice` for an order and imports the output.

## Driving it
- `$V capture invoice-csv -- python3 -m shop.invoice` → expect the header, `TEA-01,2,9.00`, `MUG-02,1,3.50`
  and `TOTAL,,12.50`.

## Expected behavior
- The header is `sku,quantity,amount`. [confirmed: spec docs/invoice-csv.md]
- Amounts are plain decimal numbers with exactly two places, such as `12.50`: no currency symbol, no
  thousands separator; the importer rejects the whole file otherwise. [confirmed: spec docs/invoice-csv.md]
- The last row is `TOTAL` with an empty quantity. [confirmed: spec docs/invoice-csv.md]

## Suspected bugs
None found.

## Open questions
- No test covers the CSV format; the spec is the only guard.

## Gotchas
- The importer is not in this repository; the spec is the contract.
