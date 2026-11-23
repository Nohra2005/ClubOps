# J-20 synthetic new-club starter set

Frozen on 2026-11-10 before running the new-club evaluation. All club names,
documents and event descriptions are synthetic. The six event labels are reused
unchanged from the already frozen `eval/synthetic-events.csv`; no new AUB policy
label was invented. The four documents per club are club-only background, dated
before every evaluated event. The run uses prefixes of 0, 1, 3 and 4 documents.

| File | Items | SHA-256 (committed LF bytes) |
|---|---:|---|
| `eval/new-club-starters.json` | 3 clubs, 12 synthetic documents | `4dcc774a8485e03907fbc403df2533635c0cb2e3ae065a4909420aef4b3a3e3d` |
| `eval/synthetic-events.csv` | 10 pre-existing synthetic events; J-20 uses S01-S05 and S10 | `bcec66154ec2dbafcd65af0e2a9e46828c5cdab11e4cd681c4372f4432a84006` |

Changing either file requires a new dated freeze entry; do not silently replace a
hash. On Windows, normalize checked-out CRLF to LF before comparing with these
committed-file hashes.

## 2026-11-11 review-driven interview freeze

Tatiana's PR #81 review identified that the president setup interview is now the
primary onboarding path (D-103). Before changing the runner, we froze four
synthetic interview answers per club in a separate file. They are club-only
background, dated before the documents and events. Evaluation stages will be
empty, 1 answer, 3 answers, all 4 answers, then all answers plus documents.
The simulation treats each added answer as if a cabinet member approved its
proposed fact in Review; it does not assert the live setup flow completed.

| File | Items | SHA-256 (committed LF bytes) |
|---|---:|---|
| `eval/new-club-interviews.json` | 3 clubs, 12 synthetic answers | `f07ab1b2fcce319d652591b98d1da6fbe262344475fb8154fc313a082ffaf480` |

Run a free pipeline check with `uv run python scripts/eval_new_club.py --system checklist`.
For a ClubOps curve, use `CLUBOPS_MODEL_MODE=replay uv run python
scripts/eval_new_club.py --system clubops --out <private-result-path>` after
synthetic model recordings exist. The runner refuses to write a ClubOps result
if any replay case lacks its recording. Checklist output is a pipeline check,
not evidence that onboarding improved planning.
