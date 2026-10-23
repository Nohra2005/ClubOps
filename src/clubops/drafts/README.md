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
