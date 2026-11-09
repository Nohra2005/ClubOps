# Learning evaluation (C-27)

C-27 now has two steps: export the evidence, then summarize Tatiana's completed
ratings. A paraphrase is not marked wrong by code. No model or wording comparator
fills the ratings. This replaces exact-word scoring for learning/answer quality
(D-87); planning evaluation and the dropped T-05/C-32 graders are unchanged.

## 1. Export the review sheet

This complete synthetic example needs no API key or network:

```sh
uv run python scripts/eval_learning.py export --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --sheet output/learning-review.csv
```

Each row runs the public learner -> individual sandbox approval -> follow-up answer
once, in a new empty in-memory store. The question is also checked before teaching.
Expected-only labels are not added to model prompts. When source and expected fact
share a column, that fact is deliberately the teaching input. Nothing touches
production knowledge.

The CSV has exactly these seven columns:

| id  | fact I expected | fact ClubOps learned | question | ClubOps's answer | learned | answer_ok |
| --- | --------------- | -------------------- | -------- | ---------------- | ------- | --------- |

- `id` preserves the original input ID if present; otherwise it is `case-0001`, etc.
- Expected facts are shown literally. For existing JSON alias groups, the first
  canonical wording is displayed; multiple facts/statements use line breaks.
- Learned facts are the actual current facts saved in that case's sandbox, including
  paraphrases or incorrect statements. Unapproved proposals are not labelled saved.
- The answer is ClubOps's actual answer text, not a suggested correct answer.
- **Both rating columns start empty.** Nothing auto-fills them, even for the fixture.

The companion `learning-review.run.json` records the run, input hash, fixed-row
hashes, execution errors and costs. It does not duplicate the private facts/questions/
answers. Keep the sheet and its matching companion together. Existing sheets or
companions are never overwritten; use a new filename for a new run.

## 2. Tatiana fills only the last two columns

Import the UTF-8 CSV into Excel or Sheets with columns treated as text, preserving
IDs, dates and line breaks. Formula-like evidence is prefixed with an apostrophe to
make it literal text. Save the completed sheet back as UTF-8 CSV.

Use `yes`, `partly` or `no` in **both** columns for **every** original row:

| Rating | learned                                                                    | answer_ok                                          |
| ------ | -------------------------------------------------------------------------- | -------------------------------------------------- |
| yes    | The expected fact was correctly saved, even with different wording         | The answer correctly uses the expected information |
| partly | Some useful information was saved but an important detail is missing/wrong | The answer is partly correct or incomplete         |
| no     | The expected fact was not saved correctly                                  | The answer is absent or incorrect                  |

For a negative case with no expected fact, judge whether no fact was invented and
whether an unknown answer is appropriate. These are case-level judgments, not an
automatic count of individual wrong/missed facts. Multiple extra/wrong learned facts
remain visible for the reviewer to consider.

Rows may be sorted. Do not edit the first five columns, remove cases, change headers
or combine rows from different runs. The scorer checks fixed-row hashes against the
companion and rejects changed, missing or duplicate evidence. These are accidental-
edit checks, not a signed or authenticated proof of who supplied the ratings.

## 3. Build the results table, offline

After the two columns are complete:

```sh
uv run python scripts/eval_learning.py score --sheet output/learning-review.csv --out output/learning-reviewed.md --json-out output/learning-reviewed.json
```

`score` does not load model configuration or call a provider. It reports separate
yes/partly/no counts for `learned` and `answer_ok`, plus a per-case table. **Partly
gets no invented numeric weight** such as 0.5. Both-yes counts are separate from
successful cases with no operational error or already-known baseline. All original
cases and failed spend remain in the denominator/cost accounting.

Blank or invalid ratings cause a nonzero exit and no results table. Exported
operational errors remain visible even after grading: the results are written, but
the command still returns exit code 2. Empty fact/answer cells mean no output was
produced; inspect an errored run's companion before treating it as poor model quality.

Result Markdown/JSON contains opaque case references, ratings, run hashes and cost/
error metadata, not the private evidence text. Replay cost is zero budget accounting,
not estimated historical provider operating cost. Configured token rates are recorded
assumptions, not verification of a provider price or reconciliation of a bill.

## Private frozen inputs

Use the actual frozen path/headers without rewriting its bytes. For example, replace
the capitalized placeholders below with the real values:

```sh
uv run python scripts/eval_learning.py export --cases PRIVATE_CSV_PATH --as-of YYYY-MM-DD --source-column SOURCE_HEADER --question-column QUESTION_HEADER --expected-column FACT_HEADER --expected-format text --id-column ID_HEADER --recordings data/private/learning-recordings --sheet data/private/learning-review.csv
uv run python scripts/eval_learning.py score --sheet data/private/learning-review.csv --out results/tmp/learning-reviewed.md --json-out results/tmp/learning-reviewed.json
```

Default input headers are `source`, `question`, `expected_facts` (JSON array), optional
`id`, `source_kind`, `club_id`. Plain single-fact cells use `--expected-format text`.
The default source kind is `user_input` and club is the isolated `eval-club`; optional
kind/club headers can also be mapped. The export preserves original IDs and hashes
the exact input snapshot. It never writes to the frozen CSV.

Tatiana confirmed her frozen headers in the PR review: `l_id`, `taught_by`,
`fact_id`, `fact`, `later_question`. The same `fact` cell can be both the teaching
input and expected fact; the question must remain a separate column. Use:

```sh
uv run python scripts/eval_learning.py export --cases PRIVATE_CSV_PATH --as-of YYYY-MM-DD --id-column l_id --source-column fact --question-column later_question --expected-column fact --expected-format text --kind-column taught_by --recordings data/private/learning-recordings --sheet data/private/learning-review.csv
```

Replace the path/date; replay still needs recordings for that exact model, date and
input. A deliberate first provider run uses the configured model and `--mode record`.
`fact_id` is not needed for collection or grading and remains in the original CSV.
Source labels are mapped only at import:

| Frozen label     | ClubOps SourceKind |
| ---------------- | ------------------ |
| chat             | chat_message       |
| after_event_form | form               |
| forwarded_email  | email              |

Every canonical SourceKind value remains accepted; an empty/missing kind defaults
to `user_input`. Unknown nonempty labels fail with a sanitized row error. No frozen
rows, canonical contracts or private evidence are changed by this mapping (D-101).

**Review CSVs intentionally contain private evidence.** For private datasets, repo-
local sheets/companions must live in ignored `data/private/` or `results/tmp/`, or
outside the repository. Never commit them, private recordings or provider keys. The
synthetic example is explicitly labelled and is not a real evaluation result.

Replay remains the default even if an ambient `.env` says live. Only deliberate
`--mode record`/`--mode live` can use a configured provider, with one shared eight-step /
$0.05 budget per case. Keep the same model, fixed `--as-of` date, input snapshot and
recordings for replay. Sandbox approval simulates an evaluator action; it is not a
real cabinet member accepting knowledge into production memory.

## Technical smoke diagnostic

The previous exact-word/citation checks remain available only under the explicit
`smoke` command for replay plumbing and regressions:

```sh
uv run python scripts/eval_learning.py smoke --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --out output/learning-smoke.md
```

Those exact-label counts are **not semantic quality scores** and must not grade the
ten private learning cases or compare model quality. Old invocations without a
subcommand now require choosing `export`, `score` or `smoke` explicitly. Real private
review and measurements remain Tatiana's T-26; final C-22 thresholds are still pending.
