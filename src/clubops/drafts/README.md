# WhatsApp draft style inputs

`draft_whatsapp` runs only after a person's click. Supply the current club ID, event ID,
verified event facts, and **approved style examples for that same club**. Store real past
messages privately, outside git. Do not add them to fixtures or model recordings in the
repository. The model sees redacted examples as style only; event facts are separate.

The output is a `Draft` with `state: draft`. A cabinet member reviews it and copies it
into WhatsApp. Nothing is sent through a WhatsApp API. Missing event facts are omitted or
left as neutral placeholders for review. The caller should save the reviewed examples
per club and provide a bounded selection (the writer uses at most five, 1200 characters
each). The model uses the existing replay/record/live client and budget.

## Cabinet acceptance (J-07/J-08)

Use three consented past events from private storage and two cabinet reviewers.
For each event, generate the eight template types from verified details and the
same club's approved style examples. Keep outputs, examples and reviewer names
private. Ask each reviewer whether they would send each draft without edits;
record required factual/style edits, apply them to the template and repeat the
review for changed outputs. A generated synthetic draft does not satisfy this gate.

The private receipt should identify event aliases, template version/commit,
reviewer aliases, date, per-template accept/edit decisions and whether every
requested edit was rechecked. Publish only aggregate completion and sanitized
code changes. Missing details stay missing; no sending or submission is part of
this review. Tatiana owns proposal agent/event integration and private scoring;
Joey owns template corrections once the two reviewers supply feedback.
