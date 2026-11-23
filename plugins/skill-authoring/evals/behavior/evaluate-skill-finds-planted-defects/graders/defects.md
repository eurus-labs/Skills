---
type: llm
---

PASS if the reply reports all four defects of the plugin, and says the eval suite was written but not run: the first skill's frontmatter `name` (`summarize-meeting-notes`) differs from its folder name (`summarize-notes`); the second skill (`digest-notes`) is missing from the `skills` array of `plugin.json`, so it would not install; the two skills' descriptions claim the same requests and neither says when not to use it, so they compete to trigger; and a step in the first skill runs `scripts/extract_actions.py`, which does not exist.
FAIL if any of the four is missing, if the reply reports a defect that is not there, if a skill or manifest was edited, or if the suite is reported as having run or any results are quoted.
