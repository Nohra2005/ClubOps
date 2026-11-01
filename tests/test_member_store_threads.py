"""Issue #45: the API's member list is one SQLite connection shared by every request thread.
Concurrent sign-in checks must not break it. Synthetic members only."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from clubops.api.security import MemberStore
from clubops.contracts.common import Role


def test_many_requests_at_once_can_read_and_write_the_member_list(tmp_path: Path) -> None:
    members = MemberStore(tmp_path)
    first = members.add("running-club", "Synthetic President", "president@example.org", Role.PRESIDENT)

    def request(n: int) -> bool:
        if n % 10 == 0:
            members.add("running-club", f"Synthetic Member {n}", f"m{n}@example.org", Role.TREASURER)
        found = members.get(first.member_id)
        return found is not None and members.by_email("president@example.org") is not None

    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
            assert all(pool.map(request, range(2000)))
        assert len(members.of_club("running-club")) == 201
    finally:
        members.close()
