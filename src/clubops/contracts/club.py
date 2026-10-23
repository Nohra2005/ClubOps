"""Standing facts about a club that forms need. No student IDs or phone numbers are stored here.

Those are supplied by the requester at submission time (``RequesterDetails``), used once,
and never written to the knowledge base or to traces.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import EmailStr, Field, SecretStr, model_validator

from clubops.contracts.common import ClubId, Contract, MemberId, Role


class Person(Contract):
    first_name: str = Field(max_length=60)
    last_name: str = Field(max_length=60)
    aub_email: EmailStr


class CabinetSeat(Contract):
    role: Role
    member_id: MemberId
    person: Person
    since: date


class GroupKind(StrEnum):
    """Clubs and faculty societies follow the same OSA process, but societies (e.g. ASME, MSFEA) use
    their faculty's rooms first, run bigger gatherings and more events with other universities."""

    CLUB = "club"
    SOCIETY = "society"


class ClubProfile(Contract):
    club_id: ClubId
    form_name: str = Field(max_length=120, description="the club's name as listed on the OSA form")
    kind: GroupKind = GroupKind.CLUB
    faculty: str | None = Field(default=None, max_length=80, description="societies only, e.g. 'MSFEA'")
    adviser: Person
    cabinet: list[CabinetSeat]
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def _faculty(self) -> Self:
        if self.faculty is not None and self.kind is not GroupKind.SOCIETY:
            raise ValueError("only a society belongs to a faculty")
        return self


class RequesterDetails(Contract):
    """Sensitive. Lives only for the duration of one draft; redacted from logs."""

    member_id: MemberId
    aub_id: SecretStr
    phone: SecretStr
