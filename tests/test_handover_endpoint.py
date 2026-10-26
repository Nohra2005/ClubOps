"""C-19: real HTTP authentication and club isolation around the deterministic handover assembly."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.contracts.common import Role
from clubops.contracts.knowhow import VerifyDecision, VerifyRequest
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from tests.factories import CLUB, NOW, actor, item, proposal

HEADERS = {"X-Requested-With": "ClubOps"}


def test_handover_is_live_for_each_role_and_never_leaks_another_clubs_facts(tmp_path: Path) -> None:
    people = MemberStore(tmp_path)
    people.add(CLUB, "Synthetic President", "president@example.com", Role.PRESIDENT)
    people.add("asme", "Other President", "other@example.com", Role.PRESIDENT)
    people.close()
    store = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    candidate = item(title="Synthetic club-specific process", statement="PRIVATE RUNNING CLUB PROCESS")
    proposed = proposal(candidate)
    store.submit(proposed)
    store.verify(VerifyRequest(proposal=proposed, decision=VerifyDecision.ACCEPT), actor(), NOW)
    store.submit(proposal(item("kh-awaiting-review", title="Synthetic unverified process"), pid="p-unverified"))
    store.close()
    config = ApiConfig(tmp_path, "synthetic-secret", dev_login=True, cookie_secure=False)
    with TestClient(create_app(config, clock=lambda: datetime(2026, 10, 26, tzinfo=UTC))) as client:
        assert client.get("/api/handover/events").status_code == 401
        assert client.post("/api/auth/dev", json={"email": "president@example.com"}, headers=HEADERS).status_code == 200
        for role in Role:
            response = client.get(f"/api/handover/{role.value}")
            assert response.status_code == 200
            assert response.json()["role"] == role.value
        guide = client.get("/api/handover/events").json()
        assert candidate.item_id in str(guide)
        assert "PRIVATE RUNNING CLUB PROCESS" in str(guide)
        assert guide["gaps"]
        assert client.get("/api/handover/nonexistent-role").status_code == 422
        client.post("/api/auth/dev", json={"email": "other@example.com"}, headers=HEADERS)
        other = client.get("/api/handover/events")
        assert other.status_code == 200
        assert candidate.item_id not in other.text
        assert "PRIVATE RUNNING CLUB PROCESS" not in other.text
        assert other.json()["sections"] == []
        assert isinstance(other.json()["gaps"], list)
