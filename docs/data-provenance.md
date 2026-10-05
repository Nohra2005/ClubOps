# Data provenance

The brief requires public, authorized or synthetic data with clear provenance.

## Sources

| Data | Source | Authorization | Where it lives |
|---|---|---|---|
| Past events, chats and handover material | **AUB Running Club only** | Consent from the cabinet members whose messages are used, recorded per source before capture | Outside the repo (`data/raw/` is ignored by git); deleted after capture |
| Extracted know-how | Produced by ClubOps from the above, verified by the cabinet | Same consent | Knowledge base; quotes capped at 500 characters |
| OSA Event Proposal form 2026–2027 | The published form, transcribed field by field | Public to AUB clubs | `data/forms/` (structure only, no answers) |
| Test fixtures | Written by the team | Synthetic | `tests/factories.py` |
| Evaluation labels | Written by the team before the system was built | Own work | `eval/` (redacted) |

## Redaction

Rule (implemented with `capture` in Phase 1): before any source reaches the model, phone numbers, AUB IDs, e-mail addresses and the names of people who did not consent are replaced with placeholders. Proposals record which kinds of data were redacted (`KnowHowProposal.redactions`).

## Limitation

All know-how comes from one club. Results show how ClubOps works for that club and do not, on their own, show that it generalizes to other clubs.
