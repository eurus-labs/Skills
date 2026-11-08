---
type: llm
---

PASS if all of these hold, judging by the reply and the files it says it wrote:
- The result is a new .pptx; `deck.pptx` itself was not overwritten.
- Only slide 2 was rebuilt; slides 1 and 3 are unchanged.
- The new slide shows the release flow as steps, not sentences: a ticket is opened, the regression suite runs, the ticket goes to the RCB for sign-off, ops deploys and closes it, with the fix-and-resubmit loop back from a failing suite.
- "RCB" is kept as written. It is not expanded into a guessed name, unless the reply flags the expansion as an assumption.
- The ticket-to-production time is shown as missing (for example `[DATA NEEDED]`, or the reply says it is unknown); no duration is invented.
- The existing speaker note about the release freeze calendar is still in slide 2's notes.

FAIL if any of these fails, or if the reply claims the slide was checked visually when nothing was rendered.
