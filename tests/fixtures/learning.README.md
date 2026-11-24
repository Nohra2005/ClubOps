# Synthetic learning replay fixture (C-27)

`learning.synthetic.csv` has one synthetic studio-booking fact and one off-topic
greeting with no expected fact. They are not AUB rules or real club material.
`learning-recordings/` contains three fake-model responses generated through the
normal recording interface with `httpx.MockTransport`, not provider calls.

The fixed evaluation date is 2026-10-29 and model ID is `fake-model`. Run from the root:

```sh
uv run python scripts/eval_learning.py export --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --sheet output/learning-review.csv
```

Replay uses no API key and no network. Expected output: two rows with actual saved
facts/answers, both rating columns blank and zero operational errors. Replay budget
cost is zero; the recording's token/cost metadata is synthetic, not measured quality
or real operating cost. Complete learned/answer_ok with yes/partly/no, then run:

```sh
uv run python scripts/eval_learning.py score --sheet output/learning-review.csv --out output/learning-reviewed.md --json-out output/learning-reviewed.json
```

Any fixture ratings are synthetic examples, not Tatiana's actual private evaluation.
The explicit `smoke` subcommand retains exact-word plumbing diagnostics only; it is
not the semantic quality scorer. The replay tests fail on incompatible prompt changes
rather than silently regenerating recordings.

On 2026-11-09, the three recordings were explicitly refreshed through the public
CLI with `httpx.MockTransport` after syncing main through `4b3f17e`. The synthetic
extraction now includes `lasting: lasting` and `stated_as: fact` (D-95), and its
request fingerprint matches the current learner prompt. The CSV, date, model and
expected outcome are unchanged. No live provider, private input or human rating
was used. Tests still require successful replay with network access forbidden.

Never put real recordings here. Keep frozen/private evaluation inputs and recordings
private; map their columns explicitly without changing the frozen CSV. Scoring rules,
human-rating workflow and limitations are documented in `web/LEARNING_EVALUATION.md`.

On 2026-11-24 the two extraction recordings were regenerated the same way (public CLI, `httpx.MockTransport`,
the same fake answers) because the extraction prompt now also lists deadlines (`learn-extract-v4`, F-316). The
answer recording is unchanged. No provider, private input or human rating was used.
