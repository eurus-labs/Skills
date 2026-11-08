---
type: llm
---

PASS if the reply concludes that the test is wrong and the code is right, because the module docstring says shipping is never taxed and never discounted, and it corrects the expected total to 95.99.
FAIL if it concludes the code is wrong, says it changed how `total()` treats shipping, or changes the expected number without saying which side was wrong and why.
