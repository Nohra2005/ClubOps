"""Add a cabinet member (or the adviser) so they can sign in. Used once per club to add its president;
after that the president adds the others from the Settings screen.

  uv run python scripts/add_member.py running-club "Full Name" name@mail.aub.edu president
"""

from __future__ import annotations

import argparse
from pathlib import Path

from clubops.api.security import MemberStore
from clubops.contracts.common import Role


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("club_id")
    parser.add_argument("name")
    parser.add_argument("email")
    parser.add_argument("role", choices=[r.value for r in Role if r is not Role.MEMBER])
    parser.add_argument("--data-dir", type=Path, default=Path("data/app"))
    args = parser.parse_args()
    store = MemberStore(args.data_dir)
    try:
        member = store.add(args.club_id, args.name, args.email, Role(args.role))
    finally:
        store.close()
    print(f"added {member.member_id} ({member.role.value}) to {member.club_id}")


if __name__ == "__main__":
    main()
