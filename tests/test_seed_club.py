"""The learning phase script (T-09): learn from a club file, review on a sheet, apply. Synthetic data only."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import httpx
import pytest
from scripts.seed_club import apply, clean_whatsapp, learn, pieces, sheet

from clubops.api.security import MemberStore
from clubops.config import ModelMode
from clubops.contracts.common import Role
from clubops.contracts.knowhow import ItemStatus
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from clubops.model.client import ModelClient
from tests.test_model_client import settings

CHAT = "[01/10/26] Sam Sample: we always book Green Field 3 weeks ahead\n[01/10/26] Lee Example: ok noted\n"
FACT = {
    "facts": [
        {
            "kind": "lesson",
            "title": "Green Field booking lead time",
            "statement": "Book Green Field 3 weeks before the event.",
            "quote": "we always book Green Field 3 weeks ahead",
            "lasting": "lasting",
            "stated_as": "fact",
            "source": 0,
            "details": {"outcome": "worked", "context": "booking the field", "recommendation": "book 3 weeks ahead"},
            "tags": ["green-field"],
        }
    ]
}


def fake_client(tmp_path: Path) -> ModelClient:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(FACT)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    return ModelClient(settings(tmp_path, ModelMode.LIVE), transport=httpx.MockTransport(handle))


def test_long_text_is_cut_on_line_breaks_into_pieces_the_learner_accepts() -> None:
    text = "".join(f"line {i} " + "x" * 50 + "\n" for i in range(400))
    parts = pieces(text, 6000)
    assert "".join(parts) == text
    assert all(len(p) <= 6000 for p in parts) and len(parts) > 3
    assert pieces("a" * 13000, 6000) == ["a" * 6000, "a" * 6000, "a" * 1000]


def test_learn_then_review_on_a_sheet_then_apply(tmp_path: Path) -> None:
    data = tmp_path / "app"
    chat = tmp_path / "chat.txt"
    chat.write_text(CHAT)
    s = settings(tmp_path, ModelMode.LIVE)
    args = argparse.Namespace(club="running-club", data_dir=data, source=[f"{chat}:chat_message"], time_budget=999.0)
    learn(args, fake_client(tmp_path), s)
    learn(args, fake_client(tmp_path), s)  # resumed: the finished piece is skipped, nothing learned twice
    state = json.loads((data / "seed-running-club.json").read_text())
    assert state["done"] == ["chat.txt#0"] and state["proposals"] == 1

    out = tmp_path / "review.csv"
    sheet(argparse.Namespace(club="running-club", data_dir=data, out=out))
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert len(rows) == 1 and rows[0]["quote"] == "we always book Green Field 3 weeks ahead"
    assert "Sam" not in rows[0]["statement"]
    assert rows[0]["share_with_all_clubs"] == "no"  # ClubOps guessed "about this club"

    rows[0]["decision"] = "approve"
    rows[0]["share_with_all_clubs"] = "yes"  # the president decides it holds for every AUB club (D-91)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    members = MemberStore(data)
    president = members.add("running-club", "Synthetic President", "president@example.org", Role.PRESIDENT)
    members.close()
    apply(argparse.Namespace(club="running-club", data_dir=data, sheet=out, member=president.member_id))

    store = KnowHowStore(open_club_store_backend(data, "running-club"))
    try:
        assert not store.pending
        assert [i.status for i in store.visible("running-club")] == [ItemStatus.VERIFIED]
    finally:
        store.close()
    other = KnowHowStore(open_club_store_backend(data, "chess-club"))
    try:
        assert [i.title for i in other.visible("chess-club")] == ["Green Field booking lead time"]
    finally:
        other.close()


def test_only_cabinet_members_of_the_club_can_apply_a_sheet(tmp_path: Path) -> None:
    out = tmp_path / "review.csv"
    out.write_text("proposal_id,decision\n")
    with pytest.raises(SystemExit):
        apply(argparse.Namespace(club="running-club", data_dir=tmp_path, sheet=out, member="m-nobody"))


def test_whatsapp_system_lines_are_dropped_before_learning() -> None:
    chat = (
        "[27/02/2025, 4:43:51 PM] Club: \u200eMessages and calls are end-to-end encrypted.\n"
        "[27/02/2025, 4:51:23 PM] Sam Sample: \u200eSam Sample joined using a group link\n"
        "\u200e[07/03/2025, 10:28:31 AM] Lee Example: \u200eimage omitted\n"
        "[12/03/2025, 3:35:23 PM] Lee Example: Starting point in front of sea gate\n"
        "continued line of the same message\n"
    )
    out = clean_whatsapp(chat)
    assert "sea gate" in out and "continued line" in out
    assert "joined" not in out and "omitted" not in out and "encrypted" not in out


def test_learning_cost_and_counts_are_tracked_without_club_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.seed_club as seed

    logged: list[tuple[str, dict[str, object], dict[str, float], dict[str, str]]] = []

    class Recorder:
        def log_run(
            self,
            name: str,
            params: dict[str, object],
            metrics: dict[str, float],
            tags: dict[str, str],
            tables: dict[str, str],
        ) -> None:
            logged.append((name, dict(params), dict(metrics), dict(tags)))

    monkeypatch.setattr(seed, "tracker", lambda experiment: Recorder())
    chat = tmp_path / "chat.txt"
    chat.write_text(CHAT)
    args = argparse.Namespace(
        club="running-club",
        data_dir=tmp_path / "app",
        source=[f"{chat}:chat_message"],
        time_budget=999.0,
        track="onboarding",
        tag=["step=1"],
    )
    learn(args, fake_client(tmp_path), settings(tmp_path, ModelMode.LIVE))
    [(name, params, metrics, tags)] = logged
    assert name == "learn running-club" and tags == {"kind": "learning", "step": "1"}
    assert metrics["pieces"] == 1 and metrics["facts"] == 1 and metrics["cost_usd"] > 0
    assert "Green Field" not in json.dumps([params, tags])  # ids, hashes and counts only
