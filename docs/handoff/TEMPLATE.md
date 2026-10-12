# Handoff log — `<area name>`

One file per area (see the ownership table in `CONTRIBUTING.md`), not per person — ownership can move, the log doesn't. Append a new entry **at the bottom** every time you stop working in this area, whether or not the work is finished. New entry goes on top only sorts "nicely" until two people append at once and git has to merge it; appending at the bottom means two concurrent entries almost never touch the same lines.

Write the entry as if explaining to a teammate (or their AI tool) who has never seen your session and is about to continue cold. Keep it short — a few lines per field is plenty. Delete nothing; superseded entries are history, not clutter.

Copy the block below for each new entry.

```
## 2026-00-00 — <your name> (<branch or PR, e.g. feat/intake-capability or PR #3>)

**Did:** one or two lines on what actually changed (not "worked on intake" — "implemented intake's happy path + the missing-start-date question; tests for both").

**State:** does it build / pass `make check`? Is it committed? Pushed? Is the PR open, draft, merged? Anything half-done that looks finished but isn't?

**Next:** the single most useful next step, concretely. Not "keep going" — "wire apply-rules to read the rule items intake already fetches" or "write the adversarial test for a prompt-injected event description before touching the happy path."

**Open questions / blockers:** anything you're unsure about, anything you decided without checking (flag it so it can be revisited), anything you're stuck on. "None" is a fine answer.
```
