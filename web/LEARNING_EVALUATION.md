# Learning evaluation (C-27)

The runner exercises the public learner, knowledge verification and cited-answer
interfaces. Each CSV row gets a new empty in-memory store. It asks before learning,
captures proposals, simulates individual evaluator approval in that sandbox, then asks
the same question again. It cannot connect to an existing production knowledge store.
Ground-truth labels are used only by the scorer, never added to model prompts.

## Offline synthetic example

From the repository root after installing the locked Python environment:

```sh
uv run python scripts/eval_learning.py --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --out output/learning-synthetic.md --json-out output/learning-synthetic.json
```

This runs with no API key or network. The committed recordings contain only synthetic
studio-booking/greeting responses, generated with a mock provider. Expected smoke result:
2 completed cases, 1 expected/learned fact, 0 unmatched/missed facts, 1 new-fact citation,
0 operational errors. Replay budget cost is zero, **not** measured provider operating
cost or evidence of model quality. The root test suite verifies this complete replay.

## CSV interface and frozen inputs

| Column           | Required | Meaning                                                                                                                                           |
| ---------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source`         | yes      | Authorized untrusted source text, nonempty and at most 20,000 characters                                                                          |
| `question`       | yes      | Follow-up question, 3–500 characters                                                                                                              |
| `expected_facts` | yes      | JSON array of labelled statements; a nested array contains pre-labelled alternative wordings for one fact. `[]` means no fact should be extracted |
| `source_kind`    | no       | Published SourceKind value: `user_input` by default; also `email`, `chat_message`, `retrospective`, `document`, etc.                              |
| `club_id`        | no       | Published club slug; defaults to isolated `eval-club`                                                                                             |

For example, `[["Use form A.", "Submit form A."], "Ask the example coordinator."]`
labels two facts, allowing two exact wordings of the first. Duplicate/overlapping
labels are refused. Names of people, original case IDs and filenames are not used as
report row labels; rows are `case-0001`, etc.

Do not rewrite a frozen private file to fit the runner. Explicitly map its headers:

```sh
uv run python scripts/eval_learning.py --cases <private-learning.csv> --as-of <YYYY-MM-DD> --source-column <source-header> --question-column <question-header> --expected-column <fact-header> --expected-format text --recordings <private-recordings> --out results/tmp/learning.md
```

`--expected-format text` treats each nonempty fact cell as one labelled statement;
the default JSON format permits multiple facts and pre-labelled aliases. Kind/club
headers can also be mapped with `--kind-column` and `--club-column`. Unknown enum values
fail validation rather than being silently guessed. The report hashes the exact bytes
of the single dataset snapshot it evaluated; it cannot overwrite the input file.

## What the numbers mean

- `facts_learned`: distinct expected labels matched by current verified facts in this
  case's club. Match = NFKC Unicode normalization, case folding, punctuation/whitespace
  normalization and otherwise exact wording. Negation is not removed.
- `wrong_facts`: distinct unmatched or wrong-scope proposals **under this exact-label
  metric**. An unmatched paraphrase is not proof of a factually false statement. Alias
  sets must be frozen before viewing model outputs; do not tune labels after the run.
- `missed_facts`: expected labels with no current verified match; duplicate proposals
  get no extra credit and have their own count.
- `answer_reused_new_fact`: the baseline was unknown and the new known answer cites a
  newly verified expected fact, with all citations visible to this case. This measures
  citation reuse, not semantic correctness of every answer claim.
- A successful positive case needs complete labels, no unmatched/duplicate proposals,
  an unknown baseline, supported citation reuse and no operational error. A negative
  case succeeds only with no proposed facts and a still-unknown answer.
- Every case remains in the denominator. Model failures/missing recordings are phase
  errors even if a capability returns a fallback. Error text is not exported. The CLI
  returns exit code 2 for operational errors, while still writing the result table.
- Cost comes from the shared per-case budget (at most $0.05 and 8 steps), including
  failed spend. Unknown cost is unavailable, not zero. Replay charges zero budget cost;
  record/live cost is usage-based accounting, not reconciliation of a provider bill.
  Reports include the configured input/output USD-per-million-token rates. A configured
  zero rate does not establish that a provider is free; verify rates before T-26 cost claims.

## Record and replay private evaluation

The default is always replay, even if an ambient `.env` says live. A deliberate
`--mode record` or `--mode live` can use the configured provider. Keep provider keys,
authorized sources and real recordings private; choose a private `--recordings` path.
Use the same model, fixed `--as-of` date, dataset snapshot and recordings for replay.
Case-local deterministic item IDs keep follow-up recording keys stable.

Reports contain opaque row references, counts, phase errors, budget metadata, model,
mode, input hash and scoring version; no sources, extracted statements or answer text.
The scoring version is `learning-exact-v1`. The task-authorized CLI composes public
interfaces; the scoring module depends on contracts, not backend implementations.

This is an isolated capture/verify/ask evaluation, not browser/email-delivery testing,
a cumulative-memory merge benchmark, human acceptance, real-provider quality evidence
or the final held-out regression thresholds. Tatiana runs the frozen private set in
T-26; C-22's final CI gates need those results. The synthetic replay test already runs
under the existing root CI without calling a provider.

Only club-scoped create proposals are approved in this empty-store experiment. Shared
AUB-policy approval and merge/update behavior against existing memory are separate tests.
