# Model trial (2026-11-05)

Which model ClubOps runs on. 5 practice events (E01, E02, E03, E10, E18: not held out), each planned by ClubOps
and by the "model + rulebook" baseline, once per model. Every run is tracked in MLflow (experiment
`model-trial`, round 2; private store). Selection rule, fixed before choosing: fewest failed runs, then most
approvals found, then lowest cost. Decision: D-90. Total spend for both rounds: $0.59.

| Model | System | Approvals caught | Wrong extras | Failed runs | Cost (5 events) | Seconds per event |
|---|---|---|---|---|---|---|
| **Claude Haiku 5.5** | ClubOps | 21 of 33 (64%); the other 12 all flagged "not sure" | 7 | **0** | $0.014 | 19 |
| Claude Haiku 5.5 | rulebook | 29 of 33 (88%) | 18 | 0 | $0.002 | 3 |
| GPT-6 Luna | ClubOps | 19 of 33 (58%) | 5 | 5 | $0.007 | 29 |
| GPT-6 Luna | rulebook | 19 of 33 (58%) | 9 | 2 | $0.001 | 9 |
| Gemini 3.7 Flash | ClubOps | 20 of 33 (61%) | 9 | 3 | $0.108 | 35 |
| Gemini 3.7 Flash | rulebook | 24 of 33 (73%) | 13 | 0 | $0.010 | 4 |
| Gemini 3.8 Flash | ClubOps | 21 of 33 (64%) | 7 | 4 | $0.078 | 29 |
| Gemini 3.8 Flash | rulebook | 24 of 33 (73%) | 14 | 0 | $0.009 | 3 |

Dropped before round 2: DeepSeek V4.1 Flash (a thinking model that used its whole answer allowance thinking and
returned nothing, F-161).

Round 1, before the fixes for F-160 and F-161, failed on most runs; it is kept in the MLflow store for the record.

**Known weakness:** the prompts were written with Claude (the coding assistant), which may suit Claude models
better; self-preference in language models is documented (arXiv 2509.26464). The scores above are measured, not
judged, but the comparison is not prompt-neutral.
