# Data provenance

Updated 24 November 2026 against merged source-policy decisions D-138/D-150/D-151/D-152. Sources must be public, authorized or synthetic. A source's existence is not evidence that consent, a pilot or an evaluation has happened.

## Source inventory

| Material | Provenance and authorization | Storage/evidence |
|---|---|---|
| AUB rules | Public OSA/AUB documents; each rule records its source and quote. The review decision is recorded separately in the design log; D-100 adds reviewed 2026 bylaws material | `data/rulebook/aub-rules.json`, D-65/D-66/D-100 |
| OSA proposal structure | Public 2026-2027 form transcribed as versioned fields, including conditional materials/catering sections; no filled personal answers | `data/forms/osa_event_proposal_2026_2027.json`, D-76 |
| Running Club histories, messages and interviews | Private cabinet material; the responsible teammate must record authorization/consent before use | Ignored `data/raw/` or external private storage; T-09/T-29, not public fixtures |
| ASME and other-club material | Separately authorized sources with their own club identity; do not treat Running Club facts as ASME evidence | T-35/T-38; no claim that collection or seeding is complete |
| Frozen evaluation rows and labels | Team-labelled private examples; freeze dates/hashes and split protocol are public | `eval/FROZEN.md`, `eval/README.md`; actual private rows stay outside git |
| Unit/browser/container fixtures | Synthetic records, public rulebook where appropriate, scripted model responses; never real cabinet identities | `tests/factories.py`, `web/src/api/fixtures.ts`, local-only test account |
| Metrics and reports | Counts, durations, model/prompt versions, outcomes and costs derived from recorded activity | Scoped run/trace metadata; scripted costs are explicitly labelled synthetic |

## Before processing a real source

For new-club onboarding, use C-21's president interview; WhatsApp message-history
import is no longer the onboarding path (D-103, confirmed by Tatiana through
Christophe on 9 November). Do not ask ASME to hand over member chats. Existing
historical experiments do not establish consent for future use. Tatiana owns the
professor discussion and any resulting policy; no answer from him is claimed here.

Record who authorized it, its source type/date, permitted purpose and club, and any required deletion restriction in a private provenance record. Do not put personal authorization records or raw source contents in the public ledger. Only genuinely public policy belongs in the shared AUB scope; a forwarded message claiming to be policy is not automatically authoritative.

The redaction component hides phone numbers, AUB IDs, emails and links before model calls. Automatic removal of every personal name is **not** claimed. Review names and identifying context manually according to the source's consent. Extraction checks quoted support, but redaction and quote validation do not replace authorization or human verification.

## Storage and deletion

- Real inputs, contact details, recordings, databases and exports stay in ignored/private runtime storage. No real data goes into tests, CI traces, image layers or committed example reports.
- Browser demo storage contains synthetic records. Local Compose seeds `president@example.com` as a clearly synthetic test identity; it is not a university account or production access policy.
- Build-context checks place synthetic canaries in excluded locations and inspect the actual BuildKit export. Provider secrets remain runtime configuration; an optional trusted-root bundle is mounted only during dependency installation.
- Interview/chat/document facts wait in Review. Under the merged trusted-mail exception (D-138, narrowed by D-151), source checks and plain code may apply a clean new OSA fact after the explicit paid read; updates/merges, contradictions and flagged mail still wait for a person. This exception is not consent to ingest arbitrary material or proof of background fetching. Applied changes retain Edit/Undo history.
- Retention and source deletion are operational responsibilities, not an implemented automatic purge. Do not claim that all raw sources have already been deleted, or that traces expire after a fixed interval, without an actual job and evidence. Private evaluation recordings may need to remain available for reproducibility under their authorization.
- A volume is persistence, not backup/recovery evidence. Keep private SQLite backups outside git and verify restoration before a production recovery claim.

The learner's debugging log is private runtime data, separate from the metadata-only
report sink. D-99 enables it by default in the data directory for diagnosing failed
extraction. Treat debug output and recordings as potentially source-derived sensitive
content; never attach them wholesale to CI, public issues or reports. Redaction is
not a guarantee that all identifying context is gone. C-27 review sheets likewise
contain expected/learned facts, questions and answers; keep actual human ratings and
their companion files private under the evaluation's authorization. D-152/#151 adds the same private human-marking boundary for the 42-question chatbot test. Exporting a blank sheet does not establish that any person rated it or that the evaluation passed.

## Limits on conclusions

Running Club material cannot establish generalization to every AUB club. Synthetic scenarios test behavior but do not establish provider quality or user benefit. Real pilot, handover, security-rate and model-comparison claims must cite measured results in `docs/evidence.md`; prepared scripts alone do not support those claims.

## Integrated setup data path (C-21, PRs #55 and #87)

The setup module labels incoming answers as Untrusted interview sources with the
club and question locator. Its active progress row stores a question index and, only
while queue submission is unfinished, extracted proposals and an answer fingerprint.
This outbox belongs under the private application data directory and persistent
volume, not Git or telemetry. Normal completion clears the active outbox fields;
that is not a secure-erasure or backup-retention guarantee. Human approval still
controls whether a proposed fact becomes retrievable knowledge.

All committed setup/browser/adapter examples are synthetic. No real ASME seed facts
were supplied or invented. Application wiring is merged in #87. The local
`web/e2e/setup-live.spec.ts` regression uses separate synthetic desktop/phone clubs,
real HTTP session cookies and SQLite, with skips rather than source extraction.
It checks progress and access controls; it does not establish consent, learned-fact
accuracy, source approval, provider cost or a completed real second-club demo.
Source review, explicit approval and deployed acceptance remain necessary; see
[CLUB_SETUP.md](../web/CLUB_SETUP.md).
