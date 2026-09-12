"""Persistent, encrypted-at-rest storage for the linked-account OAuth flow.

Stores three things, each in its own SQLite table:

- Registered OAuth clients (from Dynamic Client Registration - RFC 7591)
- Short-lived authorization codes (from the /authorize step)
- Long-lived access tokens (from the /token exchange)

Only the Datawrapper API token itself is encrypted (with Fernet, a
symmetric AEAD scheme) before it touches disk; everything else here is
non-secret bookkeeping. SQLite calls are synchronous, so every public
method runs its query in a thread via asyncio.to_thread rather than
blocking the event loop (see handlers/export.py for the same pattern and
why it matters for a shared HTTP deployment).

SQLite's file lives wherever OAUTH_STORE_PATH points (default:
oauth_store.db in the current directory). In a container deployment this
MUST be on a persistent volume - otherwise every linked account is lost
on the next restart or redeploy, and every user has to re-link.
"""

from __future__ import annotations

import asyncio
import secrets
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken

if TYPE_CHECKING:
    from pathlib import Path

AUTHORIZATION_CODE_TTL_SECONDS = 5 * 60
ACCESS_TOKEN_TTL_SECONDS = 365 * 24 * 60 * 60


@dataclass(frozen=True)
class OAuthClient:
    """A Dynamic-Client-Registration-issued OAuth client."""

    client_id: str
    redirect_uris: list[str]


@dataclass(frozen=True)
class AuthorizationCodeGrant:
    """What an authorization code carried, once consumed."""

    client_id: str
    redirect_uri: str
    code_challenge: str
    datawrapper_token: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    redirect_uris TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    encrypted_token BLOB NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS access_tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    encrypted_token BLOB NOT NULL,
    expires_at REAL NOT NULL
);
"""


class LinkedAccountStore:
    """Encrypted, file-backed storage for the linked-account OAuth flow."""

    def __init__(self, db_path: str | Path, encryption_key: str) -> None:
        self._db_path = str(db_path)
        self._fernet = Fernet(encryption_key.encode("ascii"))
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    # -- OAuth clients (Dynamic Client Registration) -----------------------

    def _register_client_sync(self, redirect_uris: list[str]) -> OAuthClient:
        client_id = secrets.token_urlsafe(16)
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO oauth_clients (client_id, redirect_uris, created_at) "
                "VALUES (?, ?, ?)",
                (client_id, "\n".join(redirect_uris), time.time()),
            )
            conn.commit()
        return OAuthClient(client_id=client_id, redirect_uris=redirect_uris)

    async def register_client(self, redirect_uris: list[str]) -> OAuthClient:
        """Register a new OAuth client and return it."""
        return await asyncio.to_thread(self._register_client_sync, redirect_uris)

    def _get_client_sync(self, client_id: str) -> OAuthClient | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT redirect_uris FROM oauth_clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        if row is None:
            return None
        return OAuthClient(client_id=client_id, redirect_uris=row[0].split("\n"))

    async def get_client(self, client_id: str) -> OAuthClient | None:
        """Look up a previously-registered client, or None if unknown."""
        return await asyncio.to_thread(self._get_client_sync, client_id)

    # -- Authorization codes -------------------------------------------------

    def _store_authorization_code_sync(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        datawrapper_token: str,
    ) -> str:
        code = secrets.token_urlsafe(32)
        encrypted_token = self._fernet.encrypt(datawrapper_token.encode("utf-8"))
        expires_at = time.time() + AUTHORIZATION_CODE_TTL_SECONDS
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO authorization_codes "
                "(code, client_id, redirect_uri, code_challenge, encrypted_token, "
                "expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    code,
                    client_id,
                    redirect_uri,
                    code_challenge,
                    encrypted_token,
                    expires_at,
                ),
            )
            conn.commit()
        return code

    async def store_authorization_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        datawrapper_token: str,
    ) -> str:
        """Issue a short-lived authorization code, returning it."""
        return await asyncio.to_thread(
            self._store_authorization_code_sync,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            datawrapper_token=datawrapper_token,
        )

    def _consume_authorization_code_sync(
        self, code: str
    ) -> AuthorizationCodeGrant | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT client_id, redirect_uri, code_challenge, encrypted_token, "
                "expires_at FROM authorization_codes WHERE code = ?",
                (code,),
            ).fetchone()
            # Single-use: delete on read regardless of whether it's still valid.
            conn.execute("DELETE FROM authorization_codes WHERE code = ?", (code,))
            conn.commit()
        if row is None:
            return None
        client_id, redirect_uri, code_challenge, encrypted_token, expires_at = row
        if expires_at < time.time():
            return None
        try:
            datawrapper_token = self._fernet.decrypt(encrypted_token).decode("utf-8")
        except InvalidToken:
            return None
        return AuthorizationCodeGrant(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            datawrapper_token=datawrapper_token,
        )

    async def consume_authorization_code(
        self, code: str
    ) -> AuthorizationCodeGrant | None:
        """Redeem a code exactly once, returning what it granted (or None)."""
        return await asyncio.to_thread(self._consume_authorization_code_sync, code)

    # -- Access tokens ---------------------------------------------------

    def _issue_access_token_sync(
        self, *, client_id: str, datawrapper_token: str
    ) -> str:
        access_token = secrets.token_urlsafe(32)
        encrypted_token = self._fernet.encrypt(datawrapper_token.encode("utf-8"))
        expires_at = time.time() + ACCESS_TOKEN_TTL_SECONDS
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO access_tokens "
                "(access_token, client_id, encrypted_token, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (access_token, client_id, encrypted_token, expires_at),
            )
            conn.commit()
        return access_token

    async def issue_access_token(
        self, *, client_id: str, datawrapper_token: str
    ) -> str:
        """Mint a long-lived access token bound to a Datawrapper token."""
        return await asyncio.to_thread(
            self._issue_access_token_sync,
            client_id=client_id,
            datawrapper_token=datawrapper_token,
        )

    def _resolve_access_token_sync(self, access_token: str) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT encrypted_token, expires_at FROM access_tokens "
                "WHERE access_token = ?",
                (access_token,),
            ).fetchone()
        if row is None:
            return None
        encrypted_token, expires_at = row
        if expires_at < time.time():
            return None
        try:
            return self._fernet.decrypt(encrypted_token).decode("utf-8")
        except InvalidToken:
            return None

    async def resolve_access_token(self, access_token: str) -> str | None:
        """Return the real Datawrapper token behind an access token, if valid."""
        return await asyncio.to_thread(self._resolve_access_token_sync, access_token)


def generate_encryption_key() -> str:
    """Generate a new Fernet key, for operators setting up TOKEN_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode("ascii")
