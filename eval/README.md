# Evaluation protocol

Written before the agentic capabilities exist, so the test sets cannot be tuned to the system.

## Ground rules

1. **Labels before systems.** Each dataset is labelled and its file hash recorded in `eval/FROZEN.md` before the capability it tests is implemented.
2. **Held-out split.** About 30% of every dataset is held out, frozen on the same date, and run only for the final report.
3. **Two labellers** for the extraction set; agreement reported.
4. **Replayable.** Every model response used in a reported number is recorded, so `make eval` reproduces the tables without API keys.
5. **Several runs** per configuration where the model is sampled; spread reported, not just the mean.

## Datasets (AUB Running Club data only, redacted)

| ID | Tests | Content | Target size |
|---|---|---|---|
| D1 | `capture` | Chat and handover excerpts with the know-how items a careful reader would extract | 150+ labelled items |
| D2 | `surface` | Upcoming-event situations with the items that should come up | 30 situations |
| D3 | `ask` | Questions with the expected answer and the items it should cite, including unanswerable ones | 60 questions |
| D4 | handover | 10 standard questions per role, answered by the outgoing cabinet | 10 × roles |
| D5 | `apply-rules`, `draft-proposal` | Event descriptions from past club events, with the required approvals and correct form answers | 40–60 events |
| D6 | adversarial | Injection attempts, fake "OSA" rules, unauthorized actions, malformed inputs | 40+ cases |

## Metrics

| Area | Metric |
|---|---|
| Capture | precision, recall, contradiction detection rate; personal data left after redaction |
| Surface | recall@5 of relevant items |
| Ask | answer accuracy, citation precision, correct "not known" rate |
| Handover | accuracy and time on the 10 questions, in three conditions: old chats only · raw knowledge dump · handover pack |
| Rules & proposal | required approvals caught / missed / false alarms; field accuracy; format errors reaching the form |
| Security | attack success rate on D6, before and after defences |
| Operations | latency p50/p95, tokens, cost, retries, failures per capability; **cost per successful packet** |

**Successful packet:** submittable (no error issues), every required approval identified, and approved by the cabinet without edits to required fields.

## Baselines

1. Manual process (timed, from interviews or a walkthrough, T-29).
2. **checklist**: a plain OSA checklist ticked by keywords, no model.
3. **plain**: one model call, no memory.
4. **rulebook**: one model call with the 25 AUB rules pasted in.
5. **clubops**: the planning agent as in the app, with the rulebook and only the facts learned from *earlier* events.

All four answer in the same form: the approval codes the event needs (`PROP`, `GUEST`, `HOST`, ...; list in
`src/clubops/evaluation/plans.py`). Scored against the president's labels: recall (approvals caught), precision,
false alarms, approvals missed but flagged "not sure", model calls and cost per event. Run:

```bash
uv run python scripts/eval_plans.py --events data/private/d5/d5-events.csv \
    --facts data/private/d5/facts-learned.csv --runs 3 --out results/plans.md
```

**Experiment tracking (MLflow):** add `--track <experiment>` (and `--tag key=value`) to log every system's run: model, prompt versions, settings, the hash of the test file, and recall, precision, false alarms, errors, cost and time per event. Install with `uv sync --extra tracking`; the store is private (`data/private/mlflow`, never committed) and holds only ids, codes and scores. Browse: `uv run --extra tracking mlflow ui --backend-store-uri sqlite:///data/private/mlflow/mlflow.db`.

`CLUBOPS_MODEL_MODE=record` makes real calls once and saves them; `replay` (default) re-runs for free. Each run has
its own recordings (`#r2`, `#r3`), so repeated runs show how much answers vary. The event files stay private; only
the result table is shared.

## Limitation

One club's data. Results describe this club and do not by themselves show that ClubOps generalizes.

## Handover test

Protocol: [`handover-test.md`](handover-test.md) (T-33, D-74). Results: `results/handover-test.md`.
