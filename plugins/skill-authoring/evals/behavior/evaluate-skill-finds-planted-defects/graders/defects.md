---
type: llm
---

PASS if the reply reports all four defects of the plugin, and says the eval suite was written but not run: the first skill's frontmatter `name` (`summarize-meeting-notes`) differs from its folder name (`summarize-notes`); the second skill (`digest-notes`) is missing from the `skills` array of `plugin.json`, so it would not install; the two skills' descriptions claim the same requests and neither the descriptions nor the 'When not to use' sections name the other skill or say which one to use, so they compete to trigger; and a step in the first skill runs `scripts/extract_actions.py`, which does not exist.
FAIL if any of the four is missing, if the reply reports a defect that is not there, if a skill or manifest was edited, or if the suite is reported as having run or any results are quoted. A plugin `name` that differs from the workspace folder name is not an invented defect, because the scaffold's folder name is arbitrary.
