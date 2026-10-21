# Handoff log — Capture from chats/emails, evaluation datasets

Owner: Tatiana Nohra (since 2026-10-21, D-08; previously Christophe El Chabab). Covers the `capture` capability (turning untrusted chat/email text into know-how proposals), and the evaluation datasets/harness in `eval/`.

See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

No entries yet — `capture`'s contract (`CaptureRequest`/`CaptureResult` in `src/clubops/contracts/knowhow.py`) and its slot in the registry exist and are contract-tested, but the capability itself isn't implemented. Start your first entry here once you begin.

## 2026-10-21 — Tatiana Nohra, with Claude (feat/model-client-and-redaction)

**Did:** Prepared the first D1 labelling pack: 40 cabinet-chat episodes (6 h silence split, D-17), redacted (D-09 plus links, D-36), selected by a fixed-seed script (D-37). Wrote `eval/d1-labelling-guide.md`. Pack and empty label sheet are in git-ignored `data/private/d1/`.

**State:** Docs only, no code changed. The episode script is a throwaway prep script; the tested parser is step 2.

**Next:** Tatiana labels 5 episodes, calibration check, then the remaining 35. Freeze the hash in `eval/FROZEN.md` before any capture code.

**Open questions / blockers:** Only `cabinet.txt` is on disk so far; members-group, tala-dm, triathlon and presidents chats still need copying into `data/raw/chats/` (presidents chat: only OSA staff messages, D-15). D-36 to D-39 are proposed, awaiting Tatiana.
