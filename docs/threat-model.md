# Threat model (lightweight)

## Assets

1. **Integrity of the club's know-how.** Wrong know-how quietly misleads every future cabinet.
2. **Outgoing actions.** Emails to sponsors and OSA, submissions and invites carry the club's reputation.
3. **Personal data.** Students' AUB IDs, phone numbers and names; sponsor contacts.
4. **Credentials.** Model API keys, mail access.

## Adversaries and failure sources

- An outsider who can get text into a chat export, an email or a sponsor reply.
- A member, or a compromised account, trying to act beyond their role.
- A former cabinet member who keeps access after handover.
- The model itself: hallucinated know-how, wrong rule applicability, runaway cost.
- A classmate or third party with access to the repository.

## Threats and mitigations

| ID | Threat | Mitigation | Evidence |
|---|---|---|---|
| T1 | Prompt injection through chats, emails or replies | Content arrives as `Untrusted`; only capture and intake read it, and they can only propose; flagged proposals need a written reason to accept | F-12, F-13 |
| T2 | Knowledge-base poisoning (fake rule or procedure) | Verified-only writes; AUB-wide rules need a president; contradictions go to a human; history kept | F-14, F-25 |
| T3 | Unauthorized or tampered action | Authenticated actor, role check, same club, payload-hash binding, expiry | F-17 to F-19, F-21 |
| T4 | Duplicate side effects on retry | Idempotency key per action | F-20 |
| T5 | Personal data leaking through traces or logs | Traces carry metadata only; requester details are secrets held for one draft | F-29 |
| T6 | Personal data leaking through the repo | Raw data never committed (`data/raw/` ignored); fixtures are synthetic; dependency audit in CI | `.gitignore`, CI |
| T7 | Cross-club leakage | Every request scoped to the actor's club; only AUB-wide rules are shared | F-17, F-30 |
| T8 | Hallucinated know-how presented as fact | Answers must cite or say "not known"; handover facts must cite verified items | F-22, F-23 |
| T9 | Former officer keeps access | Access follows the role; transfer is an approved action | planned (Phase 2) |
| T10 | Cost runaway (denial of wallet) | Per-packet budget with fallback | F-34, planned |
| T11 | API key leak | Keys only in environment variables; `.env` ignored; never in code or traces | `.env.example` |

## Out of scope

Attacks on AUB's own systems, on GitHub, or on the model provider.

## J-13 adversarial test status (2026-10-31)

`tests/security/test_attack_boundaries.py` uses synthetic inputs against the real API, learning, planner prompt and budget boundaries. It covers a forged session, adviser approval attempt, cross-club event access, an instruction in forwarded text, an unverified fake rule, and step/cost exhaustion. These checks exercise existing controls; they do not establish an injection success rate. The measured defense-off and defense-on run still needs a frozen attack set, recorded model responses, and Tatiana's results review. No rate should appear on the poster until that run exists in `results/`.

## J-13 frozen corpus (2026-11-10)

`tests/security/CORPUS.md` pins ten synthetic attacks and defines a strict scorer for independently reviewed outcomes. Every attack currently triggers the plain-code injection flag regression. That is a detector check, not a model attack success rate. The scorer refuses partial evidence and keeps attack text out of output (F-203). Tatiana must run and review the defense-off/on model comparison in a private environment, then own the `results/` evidence before any rate is reported.

Tatiana's PR #82 review identified a benign governance sentence that the detector flags. The separately frozen benign corpus and scorer now require false-positive counts beside attack success. The detector check is an explicit expected failure (F-204) until Tatiana changes her owned learning code; a green scorer test must not be read as a fixed detector.

## Report sections: security, calendar and inbox (2026-11-20)

### Security and evidence limits

The frozen J-13 corpus and scorer in `tests/security/CORPUS.md` separate attack
objectives from detector warnings. Every attack and benign example needs a
reviewed outcome in both modes before the scorer reports a rate. Unit-test
sample outcomes are test fixtures and must never appear as measured results.
The benign governance wording regression remains a strict expected failure
(F-204); Tatiana owns the learning detector and must fix or explicitly accept
that limitation. Existing API tests exercise forged sessions, cross-club access,
adviser restrictions, approval binding and model budgets using synthetic data.
They establish those tested boundaries, not general model resistance. Private
traces and the aggregate defense comparison remain T-26/J-13 acceptance work.

### Calendar and reminders

ClubOps is authoritative and only approved current plan revisions create sync
items. Stable IDs scope each item to its club; retrying or moving an item updates
that copy. Done items retain their main event and remove reminders; cancellation
removes both. SQLite queues keep failed jobs pending. Named reader ACL operations
preserve manually elevated permissions and do not grant ClubOps approval rights.
Tests use fake Google and HTTP transports; they do not prove hosted token refresh,
cabinet access, restart persistence or notification delivery.

The implemented reminder adapter uses private role calendars. D-116 instead calls
for one calendar per club and per-event invitees. That integration is not finished:
J-23 needs a separately coordinated CalendarItem contract from Tatiana, including
approved deadline cards, the add-to-calendar choice, named audience and removal
semantics. Do not deploy the old role-calendar design as D-116 acceptance. T-46
owns OAuth, tokens, approved-plan/cabinet triggers and queue draining; Christophe
owns deployed status and recovery. The live acceptance run needs explicit
approval of the actual calendar writes.

### OSA inbox

Free fetching routes cabinet forwards by a known club plus-tag. J-22 adds private
address verification, forwarded-original OSA checks, cleaned untrusted text,
explicit skip reasons and a global read-once claim. Outlook forwarding headers
are covered by the merged #93 regression (F-230). Verification codes and the OSA
allowlist remain private. No code path should send a reply or approve a fact.
Tatiana's #95 integrates the guard before a person-triggered paid read and saves
proposals to Review before recording completion; Christophe's #94 consumes that
published API. These PRs and their integration tests require independent review.

The ledger claim is a concurrency control, not a transaction spanning a model
provider and Review persistence: a crash after a paid call can still require
operator recovery or another call. Cross-club already-read behavior must be
explained as a skip, not evidence that another club has received the learned
facts. Live acceptance must cover wrong tag, unauthorized/non-OSA forward,
confirmation, no-fact, skip, retry and read-once outcomes without logging bodies.
Gmail Testing-mode tokens expire and require renewal (D-122/F-207). No live
mailbox, hosted worker or model-quality result is claimed here.
