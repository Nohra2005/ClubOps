"""Standing facts about a club that forms need. No student IDs or phone numbers are stored here.

Those are supplied by the requester at submission time (``RequesterDetails``), used once,
and never written to the knowledge base or to traces.
"""

from __future__ import annotations

from datetime import date

from pydantic import EmailStr, Field, SecretStr

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


class ClubProfile(Contract):
    club_id: ClubId
    form_name: str = Field(max_length=120, description="the club's name as listed on the OSA form")
    adviser: Person
    cabinet: list[CabinetSeat]
    version: int = Field(ge=1)


class RequesterDetails(Contract):
    """Sensitive. Lives only for the duration of one draft; redacted from logs."""

    member_id: MemberId
    aub_id: SecretStr
    phone: SecretStr
