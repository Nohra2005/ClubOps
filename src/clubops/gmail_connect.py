"""Connecting the ClubOps Gmail inbox from inside the app, and fetching it (T-47, D-156).

Same idea as the Calendar connect (D-155): the person who owns the inbox account presses Connect, Google asks for
``gmail.readonly`` only, and the refresh key is kept encrypted on the host. The inbox belongs to the whole host, not
to one club, so only an operator (``CLUBOPS_OPERATOR_EMAILS``) may connect or disconnect it. Fetching is free (no
model call): it only lists mail and applies the free checks of ``inbox_intake``. Reading a mail into Review stays a
separate click that costs one model call."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from clubops.calendar.connect import ConnectionVault, authorization_url, token_key
from clubops.gmail_access import GmailKeyError, access_token, cabinet_senders, parse_extra_senders
from clubops.inbox.capture import PendingInbox
from clubops.inbox.gmail import GmailGateway
from clubops.inbox.guards import InboxLedger
from clubops.inbox_intake import InboxNotes, intake, parse_osa_senders

TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - a public endpoint, not a secret
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
KEY = "gmail"  # the one inbox of this host, stored under this name in the vault
RECONNECT_HINT = "Gmail access ended. An operator needs to connect the ClubOps inbox again."
WRONG_ACCOUNT = "That is not the ClubOps inbox account. Sign in with the account that receives the forwarded mail."
FETCH_EVERY = timedelta(seconds=20)  # a click cannot hammer Gmail


class GmailConnectError(RuntimeError):
    """Connecting or fetching failed; the message is safe to show a person."""


@dataclass(frozen=True)
class GmailSettings:
    """The host's private Gmail settings. Missing parts mean "not set up"."""

    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None  # the older way: a key pasted in the host's settings
    redirect_uri: str | None = None
    operators: frozenset[str] = frozenset()  # people who may connect or disconnect the inbox
    address: str | None = None  # the inbox account's address; if set, only this account can be connected
    osa_senders: frozenset[str] = frozenset()
    extra_senders: Mapping[str, set[str]] | None = None
    token_key: str | None = None

    @property
    def can_connect(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri and self.operators)

    @property
    def has_key(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)


def gmail_settings_from_env(values: Mapping[str, str]) -> GmailSettings:
    operators = values.get("CLUBOPS_OPERATOR_EMAILS", "")
    return GmailSettings(
        client_id=values.get("CLUBOPS_GMAIL_CLIENT_ID") or None,
        client_secret=values.get("CLUBOPS_GMAIL_CLIENT_SECRET") or None,
        refresh_token=values.get("CLUBOPS_GMAIL_REFRESH_TOKEN") or None,
        redirect_uri=values.get("CLUBOPS_GMAIL_REDIRECT_URI") or None,
        operators=frozenset(a.strip().casefold() for a in operators.split(",") if "@" in a),
        address=(values.get("CLUBOPS_GMAIL_ADDRESS") or "").strip().casefold() or None,
        osa_senders=frozenset(parse_osa_senders(values.get("CLUBOPS_OSA_SENDERS"))),
        extra_senders=parse_extra_senders(values.get("CLUBOPS_INBOX_SENDERS")),
        token_key=values.get("CLUBOPS_CALENDAR_TOKEN_KEY") or None,  # one key locks every stored Google key
    )


class GmailService:
    def __init__(
        self,
        data_dir: Path,
        settings: GmailSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        session_secret: str = "",
    ) -> None:
        self.data_dir = data_dir
        self.settings = settings
        self.transport = transport
        self.vault = ConnectionVault(data_dir, token_key(session_secret or "dev-only-secret", settings.token_key))
        self._lock = threading.Lock()
        self._last: tuple[datetime, dict[str, int]] | None = None

    def is_operator(self, email: str) -> bool:
        return email.strip().casefold() in self.settings.operators

    # ------------------------------------------------------------ the key

    def _access_token(self) -> str:
        """The connected key, else the host's pasted key. A connected key Google ended is never swapped."""
        s = self.settings
        if self.vault.has(KEY):
            saved = None if self.vault.needs_reconnect(KEY) else self.vault.load(KEY)
            if saved is None:
                raise GmailKeyError(RECONNECT_HINT)
            try:
                return access_token(s.client_id, s.client_secret, saved, transport=self.transport)
            except GmailKeyError:
                self.vault.mark_reconnect(KEY)
                raise GmailKeyError(RECONNECT_HINT) from None
        return access_token(s.client_id, s.client_secret, s.refresh_token, transport=self.transport)

    def state(self) -> dict[str, object]:
        """No key, address or mail is ever included. ``state``: not_set_up, not_connected, connected, reconnect."""
        if self.vault.has(KEY):
            state = "reconnect" if self.vault.needs_reconnect(KEY) else "connected"
            return {"state": state, "source": "app", "can_connect": self.settings.can_connect}
        if self.settings.has_key:
            return {"state": "connected", "source": "host", "can_connect": self.settings.can_connect}
        return {
            "state": "not_connected" if self.settings.can_connect else "not_set_up",
            "source": None,
            "can_connect": self.settings.can_connect,
        }

    # ----------------------------------------------------------- connecting

    def start_connect(self, member_id: str, now: datetime) -> str:
        s = self.settings
        if not s.can_connect:
            raise GmailConnectError("The Gmail inbox is not set up on the host yet.")
        assert s.client_id and s.redirect_uri  # noqa: S101 (can_connect checked above)
        return authorization_url(s.client_id, s.redirect_uri, self.vault.begin(KEY, member_id, now), (SCOPE,))

    def finish_connect(self, member_id: str, state: str, code: str, now: datetime) -> None:
        """Check the proof, swap the code for a key, check the permission and the account, then keep it encrypted."""
        s = self.settings
        if not self.vault.consume(state, KEY, member_id, now):
            raise GmailConnectError("This connect link is not valid any more. Press Connect again.")
        if not s.can_connect:
            raise GmailConnectError("The Gmail inbox is not set up on the host yet.")
        try:
            with httpx.Client(transport=self.transport, timeout=15) as client:
                reply = client.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": s.client_id,
                        "client_secret": s.client_secret,
                        "redirect_uri": s.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                body = reply.json() if reply.status_code == 200 else {}
                refresh, access = body.get("refresh_token"), body.get("access_token")
                if not (isinstance(refresh, str) and refresh and isinstance(access, str) and access):
                    raise GmailConnectError("Google did not give access. Press Connect again and allow it.")
                if SCOPE not in str(body.get("scope", "")).split():
                    raise GmailConnectError("Reading the inbox must be allowed. Press Connect again and allow it.")
                profile = client.get(PROFILE_URL, headers={"Authorization": f"Bearer {access}"})
        except (OSError, httpx.HTTPError, ValueError):
            raise GmailConnectError("Google could not be reached. Try again in a minute.") from None
        address = str(profile.json().get("emailAddress", "")).casefold() if profile.status_code == 200 else ""
        if not address or (s.address and address != s.address):
            raise GmailConnectError(WRONG_ACCOUNT)
        self.vault.save(KEY, refresh, member_id, now)

    def disconnect(self) -> None:
        saved = self.vault.load(KEY)
        self.vault.delete(KEY)
        if saved:
            try:
                with httpx.Client(transport=self.transport, timeout=15) as client:
                    client.post(REVOKE_URL, data={"token": saved})
            except (OSError, httpx.HTTPError):
                pass

    # ---------------------------------------------------------------- fetch

    def fetch(self, now: datetime) -> dict[str, int]:
        """Free: list the inbox and apply the free checks. Two clicks within 20 seconds share one fetch."""
        s = self.settings
        with self._lock:
            if self._last and now - self._last[0] < FETCH_EVERY:
                return self._last[1]
            if not s.osa_senders:
                raise GmailConnectError(
                    "The list of OSA senders is not set on the host, so every e-mail would be skipped."
                )
            try:
                token = self._access_token()
                counts = intake(
                    GmailGateway(token, transport=self.transport),
                    PendingInbox(self.data_dir / "inbox.db"),
                    notes=InboxNotes(self.data_dir / "inbox-notes.db"),
                    ledger=InboxLedger(self.data_dir / "inbox-ledger.db"),
                    cabinet=cabinet_senders(self.data_dir, s.extra_senders),
                    osa_senders=s.osa_senders,
                    received_at=now,
                )
            except GmailKeyError as exc:
                raise GmailConnectError(str(exc)) from None
            except (OSError, httpx.HTTPError, ValueError):
                raise GmailConnectError("Gmail could not be reached. Try again in a minute.") from None
            self._last = (now, counts)
            return counts
