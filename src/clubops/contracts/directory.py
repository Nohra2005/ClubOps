"""Contacts (D-10) and assets (D-12). Cabinet-only reference data, kept outside the know-how items.

Contact details (phone, e-mail) are never sent to a model or quoted in answers: know-how items
point to a contact with ``contact_ref`` and the UI shows the details to the cabinet only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import EmailStr, Field, StringConstraints, model_validator

from clubops.contracts.common import ClubId, Contract, SourceRef

ContactId = Annotated[str, StringConstraints(pattern=r"^ct-[a-z0-9-]{2,63}$")]
AssetId = Annotated[str, StringConstraints(pattern=r"^as-[a-z0-9-]{2,63}$")]


class Contact(Contract):
    contact_id: ContactId
    club_id: ClubId | None = Field(description="None for AUB-wide contacts (offices), shared by all clubs")
    name: str = Field(min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    organization: str = Field(max_length=120, description="e.g. 'OSA', 'Hostler / Athletics', 'BLK'")
    decides: list[str] = Field(default_factory=list, description="what they approve or provide, plain words")
    preferred_channel: str | None = Field(default=None, max_length=80, description="email, in person, WhatsApp...")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    sources: list[SourceRef] = Field(default_factory=list)


class AssetKind(StrEnum):
    LOGO = "logo"
    TEMPLATE = "template"
    SIGNED_AGREEMENT = "signed_agreement"
    PHOTO = "photo"
    OTHER = "other"


class Asset(Contract):
    asset_id: AssetId
    club_id: ClubId | None = Field(description="None for AUB-wide files (official forms)")
    name: str = Field(max_length=120)
    kind: AssetKind
    owner: str = Field(max_length=120, description="whose logo or file this is")
    official: bool = Field(description="True only for files from the owner; never a redrawn copy (D-07)")
    file_ref: str = Field(max_length=300, description="where the file is stored; never the file itself")
    vector: bool = False
    width_px: int | None = Field(default=None, ge=1)
    height_px: int | None = Field(default=None, ge=1)
    allowed_uses: list[str] = Field(default_factory=list, description="e.g. 'club posters', 'not on bibs'")

    @model_validator(mode="after")
    def _size(self) -> Self:
        if not self.vector and (self.width_px is None) != (self.height_px is None):
            raise ValueError("give both width and height, or neither")
        return self
