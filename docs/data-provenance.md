# Data provenance

Updated 1 November 2026. Sources must be public, authorized or synthetic. A source's existence is not evidence that consent, a pilot or an evaluation has happened.

## Source inventory

| Material | Provenance and authorization | Storage/evidence |
|---|---|---|
| AUB rules | Public OSA/AUB documents; each rule records its source and quote. The review decision is recorded separately in the design log | `data/rulebook/aub-rules.json`, D-65/D-66 |
| OSA proposal structure | Public 2026-2027 form transcribed as versioned fields, including conditional materials/catering sections; no filled personal answers | `data/forms/osa_event_proposal_2026_2027.json`, D-76 |
| Running Club histories, messages and interviews | Private cabinet material; the responsible teammate must record authorization/consent before use | Ignored `data/raw/` or external private storage; T-09/T-29, not public fixtures |
| ASME and other-club material | Separately authorized sources with their own club identity; do not treat Running Club facts as ASME evidence | T-35/T-38; no claim that collection or seeding is complete |
| Frozen evaluation rows and labels | Team-labelled private examples; freeze dates/hashes and split protocol are public | `eval/FROZEN.md`, `eval/README.md`; actual private rows stay outside git |
| Unit/browser/container fixtures | Synthetic records, public rulebook where appropriate, scripted model responses; never real cabinet identities | `tests/factories.py`, `web/src/api/fixtures.ts`, local-only test account |
| Metrics and reports | Counts, durations, model/prompt versions, outcomes and costs derived from recorded activity | Scoped run/trace metadata; scripted costs are explicitly labelled synthetic |

## Before processing a real source

Record who authorized it, its source type/date, permitted purpose and club, and any required deletion restriction in a private provenance record. Do not put personal authorization records or raw source contents in the public ledger. Only genuinely public policy belongs in the shared AUB scope; a forwarded message claiming to be policy is not automatically authoritative.

The redaction component hides phone numbers, AUB IDs, emails and links before model calls. Automatic removal of every personal name is **not** claimed. Review names and identifying context manually according to the source's consent. Extraction checks quoted support, but redaction and quote validation do not replace authorization or human verification.

## Storage and deletion

- Real inputs, contact details, recordings, databases and exports stay in ignored/private runtime storage. No real data goes into tests, CI traces, image layers or committed example reports.
- Browser demo storage contains synthetic records. Local Compose seeds `president@example.com` as a clearly synthetic test identity; it is not a university account or production access policy.
- Build-context checks place synthetic canaries in excluded locations and inspect the actual BuildKit export. Provider secrets remain runtime configuration; an optional trusted-root bundle is mounted only during dependency installation.
- Source-derived facts wait in Review. Only an authorized person's decision makes knowledge verified; flagged sources need individual frontend review.
- Retention and source deletion are operational responsibilities, not an implemented automatic purge. Do not claim that all raw sources have already been deleted, or that traces expire after a fixed interval, without an actual job and evidence. Private evaluation recordings may need to remain available for reproducibility under their authorization.
- A volume is persistence, not backup/recovery evidence. Keep private SQLite backups outside git and verify restoration before a production recovery claim.

## Limits on conclusions

Running Club material cannot establish generalization to every AUB club. Synthetic scenarios test behavior but do not establish provider quality or user benefit. Real pilot, handover, security-rate and model-comparison claims must cite measured results in `docs/evidence.md`; prepared scripts alone do not support those claims.
