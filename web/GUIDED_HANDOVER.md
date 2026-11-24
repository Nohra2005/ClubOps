# Guided cabinet handover (C-37)

The incoming officer starts at `/handover`, through the optional Events welcome
card, their account menu, or Settings → Cabinet transition. Handover is no longer
a permanent main-navigation item. Existing bookmarks still work.

## What works with the published API

- Four short stops highlight Events, Calendar, Knowledge and Chat. Back, skip,
  pause, resume and replay remain user actions. Skipping is not evidence that an
  officer read a source or completed a real task.
- The current session's role names the introduction. A separately selected
  reference-guide role never changes permissions or the role used in chat.
- One current, cited reference entry is surfaced before the full guide. The full
  guide, sources, open questions, export and demo sign-off remain available inside
  an expandable reference. Live sign-off remains unavailable under the existing
  contract; it is not replaced with a local success receipt.
- Outgoing notes open Teach with an editable starter sentence. Nothing is sent
  until the user submits it. Notes follow the existing proposal workflow.
- Explicit role-learning help adds the authenticated role and current tour step
  to Ask's text. Users can inspect the included context, turn it off, and see the
  actual submitted question in the conversation. Teach never receives this prefix.
- A URL can suggest a reference question or an outgoing-note draft, but cannot
  enable role-learning help, change membership, or send a request by itself.
- A new club still needs its president setup interview before its cabinet tour.
  An adviser keeps read-only access to the reference; the paid chat/write tour is
  not offered to that role.

## Progress and privacy

Only version, step, status and the learning-help preference are stored. The key
includes API mode, club ID, member ID and authenticated role using a structured
encoding. Names, emails, questions and knowledge content are not stored by this
feature. New accounts/roles start fresh. Invalid or future-version data resets.
Storage denial falls back to the existing tab-memory store with its notification.

This is browser-local progress, not a cross-device invitation, a term record,
proof of training, approval or a membership transfer. A completed tour does not
approve facts, sign off a pack or claim Google Calendar delivery. Nothing starts
a model or sends an external message when a tour step opens.

## Owner integration request: next contract, not implemented routes

Tatiana (backend/contracts) and Joey (chatbot) need to agree the following before
the frontend can replace local metadata or claim a persistent tutor:

1. Server progress keyed by authenticated member, club, assigned role, cabinet
   term/transition and guide version. Reads and updates must be session-scoped;
   no caller-supplied role grants authority. Agree reset/resume/stale-version rules.
2. A president-approved transition identifying outgoing/incoming officers. A date
   reminder or chat intent can offer the flow; neither changes membership. Agree
   the lifecycle, explicit invitation approval and per-member acknowledgment.
3. Structured opt-in learning context for Ask: beginner preference, current step
   and server-confirmed role. It must retain retrieval/citations, unknown answers,
   per-user authorization and budgets. The current text prefix is an ordinary user
   question, not an instruction injected into system prompts or a proven change
   to model behavior. Context must not enter Teach as club knowledge.
4. Outgoing interviews may reuse the existing gap/approval contracts, but need
   published HTTP views for durable drafts, review decisions and signed guide
   versions. The frontend has not guessed those endpoints or changed sign-off.

The proposed split is Christophe for tour, UI and handover view; Tatiana for
authenticated transition/progress contracts; Joey for retrieved tutoring behavior.
Coordinate with T-33 before measuring the redesigned experience. Existing frozen
handover results are not results for this new UI.

## Verification

`npm run check` covers the production build and progress/prefix unit tests.
`npm run test:e2e:http -- role-learning.spec.ts` checks the published HTTP boundary
with synthetic responses on desktop and phone: resume/skip/replay, actual visible
navigation targets, no automatic writes, session-role context, unchanged Teach,
adviser access, storage failure, viewport fit and automated accessibility. Existing
demo export/sign-off and actual-API reference tests also exercise the expandable
guide. Scripted responses do not measure a real model's teaching quality.


## 24 November integration status

Main merged J-15 chat API wiring in #149 (D-200): cabinet Ask now uses the
source-gated core for the authenticated club and returns dated source labels.
The earlier placeholder limitation in the C-37 handoff is historical. The role
prefix still uses the existing text API; no structured teaching contract,
server-stored term progress or measured tutor behavior is implied by this merge.
T-33's evaluation still needs to measure this redesigned walkthrough separately.
