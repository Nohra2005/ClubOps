"""Every button on a disagreement or merge card works through the real API (F-245).

The Review screen sends keep_a, keep_b, merge, both and keep_both, and sends the Edit dialog's text with a plain
approve. The server used to accept only approve, reject and edit, so all of those answered 422 or lost the text.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_learning import BLK, HEADERS, LESSON, Provider, app_client  # noqa: F401 (fixture)

NEWER = {**LESSON, "statement": "Tell Cafe B two days before a run.", "quote": "two days before"}


def _known(c: TestClient, provider: Provider) -> str:
    provider.answers.append({"facts": [LESSON]})
    review_id = c.post("/api/chat/teach", json={"text": BLK}, headers=HEADERS).json()["review_id"]
    assert c.post(f"/api/review/{review_id}", json={"decision": "approve"}, headers=HEADERS).status_code == 200
    [known] = c.get("/api/knowledge?tab=tips").json()
    return str(known["item_id"])


def _card(c: TestClient, provider: Provider, target: str, op: str) -> dict[str, object]:
    provider.answers.append({"facts": [NEWER]})
    provider.answers.append({"matches": [{"fact": 0, "op": op, "target": target, "why": "x"}]})
    c.post("/api/chat/teach", json={"text": "Now it is enough to tell Cafe B two days before a run."}, headers=HEADERS)
    [card] = c.get("/api/review").json()
    return dict(card)


def _statements(c: TestClient) -> list[str]:
    return sorted(k["statement"] for k in c.get("/api/knowledge?tab=tips").json())


@pytest.mark.parametrize(("op", "kind"), [("contradiction", "disagreement"), ("update", "merge")])
def test_keep_a_and_merge_make_the_new_version_win(app_client, op: str, kind: str) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    card = _card(c, provider, _known(c, provider), op)
    assert card["type"] == kind
    decision = "keep_a" if op == "contradiction" else "merge"
    assert c.post(f"/api/review/{card['id']}", json={"decision": decision}, headers=HEADERS).status_code == 200
    assert _statements(c) == [NEWER["statement"]]


def test_keep_b_leaves_the_known_fact_and_drops_the_proposal(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    card = _card(c, provider, _known(c, provider), "contradiction")
    assert c.post(f"/api/review/{card['id']}", json={"decision": "keep_b"}, headers=HEADERS).status_code == 200
    assert _statements(c) == [LESSON["statement"]] and c.get("/api/review").json() == []


def test_both_are_true_needs_the_context_and_keeps_both(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    card = _card(c, provider, _known(c, provider), "contradiction")
    assert c.post(f"/api/review/{card['id']}", json={"decision": "both"}, headers=HEADERS).status_code == 422
    done = c.post(f"/api/review/{card['id']}", json={"decision": "both", "reason": "Cafe B in summer"}, headers=HEADERS)
    assert done.status_code == 200 and done.json()["status"] == "approved"
    statements = _statements(c)
    assert LESSON["statement"] in statements
    assert any(s.startswith(NEWER["statement"]) and s.endswith("Context: Cafe B in summer") for s in statements)
    assert c.get("/api/review").json() == []


def test_keep_both_on_an_update_card_adds_it_as_a_new_fact(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    card = _card(c, provider, _known(c, provider), "update")
    assert c.post(f"/api/review/{card['id']}", json={"decision": "keep_both"}, headers=HEADERS).status_code == 200
    assert _statements(c) == sorted([LESSON["statement"], NEWER["statement"]])


def test_the_edit_dialog_text_is_not_dropped_when_sent_with_approve(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    provider.answers.append({"facts": [LESSON]})
    review_id = c.post("/api/chat/teach", json={"text": BLK}, headers=HEADERS).json()["review_id"]
    body = {"decision": "approve", "edited_text": "Tell Cafe B ten days before, at https://example.test/cafe."}
    assert c.post(f"/api/review/{review_id}", json=body, headers=HEADERS).status_code == 200
    assert _statements(c) == [body["edited_text"]]


def test_a_suggested_edit_goes_to_review_and_changes_the_fact_only_when_approved(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    known = _known(c, provider)
    text = "Tell Cafe B ten days before a run: https://example.test/cafe"
    reply = c.post(f"/api/knowledge/{known}/edit", json={"text": text}, headers=HEADERS)
    assert reply.status_code == 200
    assert _statements(c) == [LESSON["statement"]]  # unchanged until someone approves
    [card] = c.get("/api/review").json()
    assert card["id"] == reply.json()["review_id"] and card["statement"] == text
    assert c.post(f"/api/review/{card['id']}", json={"decision": "merge"}, headers=HEADERS).status_code == 200
    assert _statements(c) == [text]


def test_a_suggested_retirement_goes_to_review_and_removes_the_fact_when_approved(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, provider = app_client
    known = _known(c, provider)
    reply = c.post(f"/api/knowledge/{known}/retire", headers=HEADERS)
    assert reply.status_code == 200 and _statements(c) == [LESSON["statement"]]
    assert (
        c.post(f"/api/review/{reply.json()['review_id']}", json={"decision": "approve"}, headers=HEADERS).status_code
        == 200
    )
    assert c.get(f"/api/knowledge/{known}").json()["status"] == "retired"  # kept as history, no longer used


def test_editing_a_fact_that_does_not_exist_answers_404(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    c, _ = app_client
    assert c.post("/api/knowledge/nope/edit", json={"text": "Something new."}, headers=HEADERS).status_code == 404


def test_add_as_new_rule_works_on_a_suggested_edit(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    """F-249: the suggested edit carries the old fact's id; adding it next to the original needs its own id."""
    c, provider = app_client
    known = _known(c, provider)
    text = "Tell Cafe B ten days before a run: https://example.test/cafe"
    review_id = c.post(f"/api/knowledge/{known}/edit", json={"text": text}, headers=HEADERS).json()["review_id"]
    reply = c.post(f"/api/review/{review_id}", json={"decision": "keep_both"}, headers=HEADERS)
    assert reply.status_code == 200
    assert _statements(c) == sorted([LESSON["statement"], text])
    assert c.get(f"/api/knowledge/{known}").json()["statement"] == LESSON["statement"]  # the old one is untouched


def test_a_retirement_card_says_so_and_keeping_it_leaves_the_fact_active(app_client) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    """F-250: the screen needs op=retire to tell the reviewer what Approve will do."""
    c, provider = app_client
    known = _known(c, provider)
    review_id = c.post(f"/api/knowledge/{known}/retire", headers=HEADERS).json()["review_id"]
    [card] = c.get("/api/review").json()
    assert card["id"] == review_id and card["op"] == "retire"
    assert c.post(f"/api/review/{review_id}", json={"decision": "reject"}, headers=HEADERS).status_code == 200
    assert c.get(f"/api/knowledge/{known}").json()["status"] != "retired"
