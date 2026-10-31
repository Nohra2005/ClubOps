# Handover test (T-33)

**Question:** can a new cabinet member find how things are done in the club faster and more correctly with ClubOps than with what a new cabinet gets today (the old WhatsApp chats and files)?

This is the poster's headline claim, so the protocol is fixed **before** anyone sees ClubOps's answers to these questions. Decided 31 October 2026 (D-74).

## Who

- **8 volunteers** (AUB students) who never held a Running Club cabinet role: students from other clubs (ASME), playing the "new cabinet".
- Not on the team, not graders of the planning evaluation, and they haven't seen ClubOps before.
- Each gives about 40 minutes and agrees in writing (consent line at the top of the answer sheet); answers are kept without names (V1 to V8).

## The questions

- **10 questions** about running a Running Club event, taken from the frozen chatbot test (`eval/FROZEN.md`, Freeze 1), each with a known answer that is (a) somewhere in the old chats or files and (b) in the club's approved facts. Example: "How far ahead do we book Hostler?", "Who do we contact for free coffee at the cafe?".
- Split into **Set 1 and Set 2** of 5, matched so each set has the same mix of easy and hard questions (Tatiana labels difficulty before the test).
- The question list and answer key stay private (`clubops-raw/eval/`), like every real-data test set.

## Design: each person does both

| Group | Volunteers | First 5 questions | Last 5 questions |
|---|---|---|---|
| A | V1 to V4 | Set 1 with **old chats and files** | Set 2 with **ClubOps** |
| B | V5 to V8 | Set 1 with **ClubOps** | Set 2 with **old chats and files** |

Every question is answered 4 times with each method, and each method comes first for half the people, so neither the questions nor tiredness favour one side.

- **Old chats and files:** a redacted copy of the club's WhatsApp exports and its documents (phone numbers, IDs and e-mails removed), searched any way they like.
- **ClubOps:** the full app as a new cabinet member would use it: the chatbot, the handover guide for their role, and Knowledge search. If the chatbot (J-15) is not working by **12 November**, this part uses the handover guide and Knowledge search only, and the report says so.

## Rules during the test

- Up to **5 minutes per question**; "I couldn't find it" is a valid answer.
- No asking other people, no web search.
- For each answer the volunteer writes the answer, where they found it, and how sure they are (1 to 5). Time is recorded per question.

## Scoring

- Each answer is scored **correct / partly correct / wrong / not found** against the answer key, by Marc, who does not see which method was used (answers are shuffled and stripped of the method before scoring).
- Results per method: share of correct answers, share of wrong answers given with confidence 4 or 5 (confidently wrong is the worst case), median time per question, and median confidence.
- With 8 people the result is reported as it is, per question and per person, with the spread; no strong statistical claims.

## Before running it

1. T-09: the club's approved facts are loaded (otherwise ClubOps cannot know the answers).
2. C-19 (done) and, if ready, J-15 on the deployed app (C-18) or a local run.
3. Tatiana reads every question once more for clarity (no outside dry run).

**When:** 12 to 18 November. Results go to `results/handover-test.md`; the evidence ledger (`docs/evidence.md`) points the poster claim there.
