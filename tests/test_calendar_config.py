"""Private per-club Calendar IDs remain a validated backend-only mapping."""

from __future__ import annotations

import pytest

from clubops.calendar.config import calendar_ids_from_json


def test_multiple_clubs_have_separate_calendar_ids() -> None:
    mapping = calendar_ids_from_json('{"running-club":"synthetic-one","math-club":"synthetic-two"}')
    assert mapping == {"running-club": "synthetic-one", "math-club": "synthetic-two"}
    assert calendar_ids_from_json("") == {}


@pytest.mark.parametrize(
    "raw",
    [
        '["synthetic-one"]',
        '{"running-club":""}',
        '{"running-club":null}',
        '{"Running Club":"synthetic-one"}',
        '{"running-club":"synthetic-one","running-club":"synthetic-two"}',
        '{"running-club":',
    ],
)
def test_invalid_mapping_is_rejected_without_echoing_ids(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid per-club calendar configuration") as error:
        calendar_ids_from_json(raw)
    assert "synthetic-one" not in str(error.value)
    assert "synthetic-two" not in str(error.value)
