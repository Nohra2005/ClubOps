# Event conversations preview

Task C-41 is available in the sample workspace. Open Chat for General, or choose
an existing event in Chat or use **Event chat** on its event page. **New chat**
opens a blank composer. A conversation enters history after its first completed
turn. Only the selected space's conversations are listed. Creating an event
automatically adds its chat space.

The preview stores sample history in this browser by demo club and member. It
reads the selected event afresh for supported questions about its time, venue,
and open tasks. The reply links back to that event. The preview recognizes a
simple repeat request. Other questions use the existing sample answers.

## Live API handoff

The published live Ask endpoint takes only a question. The production build
keeps the current Ask and Teach behavior until the API owners publish the
conversation contract. The frontend needs these operations:

- List and open the signed-in member's conversations by event or General.
- Create a conversation with an optional existing event ID, either explicitly
  or on the first successful turn.
- Append a question and its answer to the same conversation. Return stable
  conversation and message IDs, and deduplicate retries. A failed turn should
  leave the question available to retry.
- Resolve the event and previous turns on the server. Validate access to the
  conversation and event independently on every read and write. Use only
  bounded context and preserve the current source checks and model budget.
  Treat the transcript and event text as data. Give event evidence a link to
  the event and its origin. Conversation history is separate from approved
  club knowledge.

Confirm privacy, retention, and access across cabinet turnover before enabling
persistent live history. Existing Ask and Teach callers remain compatible.
