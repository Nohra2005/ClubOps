# Frozen test sets

The test sets were written and frozen **before** the planner (T-14) and chatbot (T-17) were built, so they could not be tuned to the system (eval/README.md, rule 1). The files hold real club data and stay private (`data/private/d5/`, project `clubops-raw/eval/`); only their hashes are here. Any later change to a file changes its hash and must be recorded below as a new, dated entry with the reason.

## Freeze 1: Running Club (2026-10-22)

Labelled by Tatiana Nohra (president). Held-out split: random, seed 503; held-out items are run only for the final report.

| File | Items | Held out | SHA-256 |
|---|---|---|---|
| `d5-events.csv` | 19 past events (2 dropped) | E06, E07, E08, E13, E17, E19 | `b0249b4093d960b88b45e9893d2f54ddebd2f84e10dfb30a3387c18a3a0e4421` |
| `chatbot-questions.csv` | 42 questions (12 'not sure') | Q02, Q03, Q06, Q08, Q09, Q21, Q25, Q27, Q28, Q30, Q36, Q40, Q41 | `9a18c8777e0150ecba4ac4e33d78b477eec3d5bd34f879f86bbf052f5624a47e` |
| `learning-test.csv` | 10 fact/question pairs | L06, L08, L09 | `7a0aa5777ff4b9a62d666102549f840e9ff27ae3cc36eec364c688bb580a7f3a` |
| `facts-learned.csv` | facts stated by the president, each tagged with its source event | — | `64f461674683c4a676433b1ecf801164dde3e1befbcb91b2797205faa89a2a49` |
| `approval-codes.md` | approval code key | — | `e6d32f0ba65a3bb64e6d1e632295dfaf6967a4048fa2ace1b0e172cab767dab3` |

No leakage: when ClubOps plans a test event, it only knows facts tagged with earlier events (`learned_from_event`) and the AUB documents.

### Amendment to Freeze 1 (2026-11-25)

Tatiana removed one fact and its question because she cannot confirm that "the AUB pool is free for all AUB students" holds for events: fact F30 in `facts-learned.csv` and question Q14 in `chatbot-questions.csv`. No other ID was renumbered, and Q14 was not a held-out item. The first live run (13 of 41 counted, results/chatbot-evaluation.md) was made before this change and still includes Q14; it stays as the reported baseline.

| File | Items after | Old SHA-256 | New SHA-256 |
|---|---|---|---|
| `chatbot-questions.csv` | 41 questions | `9a18c8777e0150ecba4ac4e33d78b477eec3d5bd34f879f86bbf052f5624a47e` | `bc880d81240cb677fabd0d36574df81a5baed554cf0e7492715243168ac33473` |
| `facts-learned.csv` | 34 facts (F30 removed) | `64f461674683c4a676433b1ecf801164dde3e1befbcb91b2797205faa89a2a49` | `f96060bcbd673841c00b0e60b23af8b43d21c60be722763529de15819c4a9c7f` |

## Freeze 2: other clubs and made-up events (2026-11-04)

All items are held out: none were used while building ClubOps. Frozen before the generalization run (D-50).

| File | Items | Labelled by | SHA-256 |
|---|---|---|---|
| `asme-events.csv` (private, `data/private/asme/`) | 13 past ASME events (A08 and A11 dropped: not remembered) | ASME president (Alexis), correcting a written guess; unedited items kept as guessed, as he asked | `2ec3798e5618cd2d7f3db2c1370dac665caf23a8998ea6486ee71746fb9cd018` |
| `eval/synthetic-events.csv` (public, synthetic) | 10 made-up events, one per event type the Running Club never ran | Joey (J-14), checked and corrected by Tatiana (S06, S07, S08) | `bcec66154ec2dbafcd65af0e2a9e46828c5cdab11e4cd681c4372f4432a84006` |

Finding while labelling: ASME spent over $200 twice (A01, A07) without the members' vote our rulebook asks for, and OSA still approved. The labels record what really happened.

## ASME onboarding leak check (T-44, to fill on the onboarding day)

ASME starts empty and its president answers the setup interview (D-103) on 18 or 19 November 2026. Its 13 test events are in Freeze 2 above.

| Check | Result |
|---|---|
| Date of the setup interview | _to fill_ |
| Interview answers name any of the 13 test events (A01-A15) or their outcomes? | _to fill: list question numbers, or "none"_ |
| An answer gives away a labelled approval or deadline for a test event? If yes, that answer is removed before the run | _to fill_ |
| Cards approved / rejected / edited by the president, reviewed like a busy president (no special care) | _to fill: counts only_ |
| Answers and cards kept in `data/private/asme/` (never in Git) | _to fill_ |

