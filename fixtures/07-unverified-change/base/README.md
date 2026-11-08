# resetkit

Password-reset tokens: issue one for an account, redeem it once to set a new password.

```python
from resetkit.tokens import ResetTokens
tokens = ResetTokens(accounts)
token = tokens.issue("ana", now)
tokens.reset_password(token, "new password", now)
```
