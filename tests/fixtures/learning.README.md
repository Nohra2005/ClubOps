# Synthetic learning replay fixture (C-27)

`learning.synthetic.csv` has one synthetic studio-booking fact and one off-topic
greeting with no expected fact. They are not AUB rules or real club material.
`learning-recordings/` contains three fake-model responses generated through the
normal recording interface with `httpx.MockTransport`, not provider calls.

The fixed evaluation date is 2026-10-29 and model ID is `fake-model`. Run from the root:

```sh
uv run python scripts/eval_learning.py --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --out output/learning-synthetic.md --json-out output/learning-synthetic.json
```

Replay uses no API key and no network. Expected output: two completed cases, one
expected/learned fact, zero wrong/missed facts, one new-fact citation, zero operational
errors. Replay budget cost is zero; the scripted recording's token/cost metadata is
synthetic, not a quality or real provider-cost result. The full pipeline replay test
fails on incompatible prompt changes rather than silently regenerating these files.

Never put real recordings here. Keep frozen/private evaluation inputs and recordings
private; map their columns explicitly without changing the frozen CSV. Scoring rules,
alias restrictions and limitations are documented in `web/LEARNING_EVALUATION.md`.
