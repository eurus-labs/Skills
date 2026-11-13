# Invoice CSV

The accounting system imports one CSV per order. Its importer is strict:

- The header is `sku,quantity,amount`.
- One row per cart line, then a `TOTAL` row with an empty quantity.
- **Amounts are plain decimal numbers with exactly two places, such as `12.50`.** No currency symbol, no
  thousands separator. The importer rejects the whole file otherwise.
