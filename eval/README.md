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

1. Manual process (timed, from interviews or a walkthrough).
2. Plain checklist, no model.
3. One prompt, no memory.
4. One prompt with the club's know-how in context.
5. Full ClubOps, single agent, then multi-agent. Specialist roles stay only if they beat the single agent.

## Limitation

One club's data. Results describe this club and do not by themselves show that ClubOps generalizes.
