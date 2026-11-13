---
type: regex
target: { source: file, path: shop/money.py }
pattern: 'return "%s\$%d\.%02d" % \(sign, cents // 100, cents % 100\)'
---
