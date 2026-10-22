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

## Freeze 2: other clubs (pending, T-38)

ASME events (T-35) and one made-up event per missing event type (T-36), frozen before the generalization run (D-50).
