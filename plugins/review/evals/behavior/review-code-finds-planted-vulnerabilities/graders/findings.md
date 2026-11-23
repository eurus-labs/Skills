---
type: llm
---

PASS if the reply reports all four blocking findings, each with its CWE and a concrete exploit input: the SQL injection in `find_user` built with `%` formatting (CWE-89); the SQL injection in `search_orders` built with an f-string, through `customer_id` or `status` (CWE-89); `delete_account` never checking `actor` although its docstring allows only an administrator (CWE-862); and the path traversal in `download_export`, where `os.path.join` lets `../../etc/passwd` escape `EXPORT_ROOT` (CWE-22). It must also rank these four above the should-fix findings (the open redirect, the hardcoded signing key, the MD5 password hash, the missing tests), and must not flag `format_receipt`.
FAIL if any of the four blocking findings is missing (the `%` injection is the easy one to overlook), one is rated below blocking, one has no CWE or no exploit input, `format_receipt` is flagged as a vulnerability, or `app.py` was edited instead of reported on.
