# Chatbot evaluation (2026-11-24)

The private 42-question test (T-04, frozen) run live on Claude Haiku 5.5 through `scripts/eval_chat.py`. Counts only: the
questions, the answers and the marking sheet are private and stay out of Git. Decision D-152: the president marks the
answers (yes / partly / no, and whether the cited facts support the answer); code counts them.

## Result

41 questions (Q18 left out, see below). Total cost $0.0131.

| Questions | Correct | Partly | Wrong | Missed (said "not sure") | Correct "not sure" | Invented | Sources OK | Errors |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 41 | 13 | 1 | 0 | 16 | 11 | 0 | 14 of 14 | 0 |

- **When it answers, it is right.** 14 answers: 13 correct, 1 partly, 0 wrong, and every cited fact supports its answer.
- **It never invents.** All 11 questions whose right reply is "not sure" got "not sure".
- **Coverage is about half.** It answered 14 of the 30 questions that have an answer. It said "not sure" on the other 16.
  The facts for those 16 are not in the store (mostly facts that come from chats), so this is a gap in the club's
  knowledge, not a wrong answer. Fewer questions were answered than a full store would allow.

## How the test was run, and what was left out

1. First run, the club's real approved facts only (115 facts): 8 of 30 answered. The 35 facts the president stated on
   22 Oct (F01 to F35) were never approved into the real store.
2. The president chose to test on a **separate copy** of the store with those 35 facts loaded (`scripts/make_eval_store.py`).
   The real Knowledge was not changed. Second run, 151 facts: 14 of 30 answered. These are the figures above.
3. **Q18 is left out of the count.** Its right reply is "not sure", but fact F32 (loaded into the test copy) states the
   answer. The chatbot answered from F32, which is correct, so counting it as "invented" would be wrong.
   (`scripts/eval_chat.py score --exclude Q18`; a future run can use `make_eval_store.py --skip F32`.)
4. The first live run failed on a cut-off answer (answer limit too small, F-319); one failed question no longer stops a
   run (F-320). A phone number the model only saw as a placeholder is filled back from the cited fact (F-321).

## Known limits

- One run, one marker (the president), one model. The marker is also the author of the 35 stated facts.
- The 42 questions were frozen before the chatbot was built; 13 are held out (`eval/freeze.json`).
