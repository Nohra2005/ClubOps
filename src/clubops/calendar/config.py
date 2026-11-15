"""Parse private per-club Google Calendar IDs supplied by the backend."""

from __future__ import annotations

import json

from pydantic import TypeAdapter, ValidationError

from clubops.contracts.common import ClubId

_CLUB_ID = TypeAdapter(ClubId)
_ERROR = "invalid per-club calendar configuration"


def calendar_ids_from_json(raw: str) -> dict[str, str]:
    """Return a club-to-calendar map without exposing private IDs in errors."""
    if not raw.strip():
        return {}

    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(_ERROR)
            result[key] = value
        return result

    try:
        parsed = json.loads(raw, object_pairs_hook=unique_pairs)
        if not isinstance(parsed, dict):
            raise ValueError(_ERROR)
        result: dict[str, str] = {}
        for club_id, calendar_id in parsed.items():
            _CLUB_ID.validate_python(club_id)
            if not isinstance(calendar_id, str) or not calendar_id.strip():
                raise ValueError(_ERROR)
            result[club_id] = calendar_id.strip()
        return result
    except (json.JSONDecodeError, ValidationError, ValueError):
        raise ValueError(_ERROR) from None
