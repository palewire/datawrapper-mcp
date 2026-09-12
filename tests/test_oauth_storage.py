"""Tests for the linked-account OAuth flow's persistent storage."""

import time

import pytest
from cryptography.fernet import Fernet

from datawrapper_mcp.oauth.storage import LinkedAccountStore, generate_encryption_key


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "oauth_store.db"
    return LinkedAccountStore(db_path=db_path, encryption_key=generate_encryption_key())


def test_generate_encryption_key_produces_valid_fernet_key():
    key = generate_encryption_key()
    # Constructing a Fernet with it should not raise.
    Fernet(key.encode("ascii"))


async def test_register_and_get_client(store):
    client = await store.register_client(["https://claude.ai/api/mcp/auth_callback"])

    fetched = await store.get_client(client.client_id)

    assert fetched is not None
    assert fetched.client_id == client.client_id
    assert fetched.redirect_uris == ["https://claude.ai/api/mcp/auth_callback"]


async def test_get_client_returns_none_for_unknown_id(store):
    assert await store.get_client("does-not-exist") is None


async def test_authorization_code_round_trip(store):
    code = await store.store_authorization_code(
        client_id="client-1",
        redirect_uri="https://claude.ai/api/mcp/auth_callback",
        code_challenge="abc123",
        datawrapper_token="dw-secret-token",
    )

    grant = await store.consume_authorization_code(code)

    assert grant is not None
    assert grant.client_id == "client-1"
    assert grant.redirect_uri == "https://claude.ai/api/mcp/auth_callback"
    assert grant.code_challenge == "abc123"
    assert grant.datawrapper_token == "dw-secret-token"


async def test_authorization_code_is_single_use(store):
    code = await store.store_authorization_code(
        client_id="client-1",
        redirect_uri="https://claude.ai/api/mcp/auth_callback",
        code_challenge="abc123",
        datawrapper_token="dw-secret-token",
    )

    first = await store.consume_authorization_code(code)
    second = await store.consume_authorization_code(code)

    assert first is not None
    assert second is None


async def test_unknown_authorization_code_returns_none(store):
    assert await store.consume_authorization_code("never-issued") is None


async def test_expired_authorization_code_is_rejected(store, monkeypatch):
    code = await store.store_authorization_code(
        client_id="client-1",
        redirect_uri="https://claude.ai/api/mcp/auth_callback",
        code_challenge="abc123",
        datawrapper_token="dw-secret-token",
    )

    # Jump the clock past the code's short TTL.
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 10_000)

    assert await store.consume_authorization_code(code) is None


async def test_access_token_round_trip(store):
    access_token = await store.issue_access_token(
        client_id="client-1", datawrapper_token="dw-secret-token"
    )

    resolved = await store.resolve_access_token(access_token)

    assert resolved == "dw-secret-token"


async def test_unknown_access_token_returns_none(store):
    assert await store.resolve_access_token("never-issued") is None


async def test_expired_access_token_is_rejected(store, monkeypatch):
    access_token = await store.issue_access_token(
        client_id="client-1", datawrapper_token="dw-secret-token"
    )

    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 365 * 24 * 60 * 60 + 1)

    assert await store.resolve_access_token(access_token) is None


async def test_token_is_encrypted_at_rest(store, tmp_path):
    """The plaintext Datawrapper token should never appear in the raw db file."""
    secret = "dw-super-secret-value-xyz"
    await store.issue_access_token(client_id="client-1", datawrapper_token=secret)

    db_path = next(tmp_path.glob("*.db"))
    raw_bytes = db_path.read_bytes()

    assert secret.encode("utf-8") not in raw_bytes


async def test_different_stores_cannot_decrypt_each_others_tokens(tmp_path):
    store_a = LinkedAccountStore(
        db_path=tmp_path / "a.db", encryption_key=generate_encryption_key()
    )
    store_b = LinkedAccountStore(
        db_path=tmp_path / "b.db", encryption_key=generate_encryption_key()
    )

    access_token = await store_a.issue_access_token(
        client_id="client-1", datawrapper_token="dw-secret-token"
    )

    # Manually copy the row into store_b's db using store_a's ciphertext -
    # simulating a key mismatch - to confirm decryption fails closed.
    # `with sqlite3.connect(...)` only commits/rolls back on exit, it doesn't
    # close the connection, so close() is called explicitly to avoid leaking
    # the file handle (and the ResourceWarning that comes with it).
    import sqlite3
    from contextlib import closing

    with closing(sqlite3.connect(store_a._db_path)) as conn_a:
        row = conn_a.execute(
            "SELECT access_token, client_id, encrypted_token, expires_at "
            "FROM access_tokens WHERE access_token = ?",
            (access_token,),
        ).fetchone()
    with closing(sqlite3.connect(store_b._db_path)) as conn_b:
        conn_b.execute(
            "INSERT INTO access_tokens "
            "(access_token, client_id, encrypted_token, expires_at) "
            "VALUES (?, ?, ?, ?)",
            row,
        )
        conn_b.commit()

    assert await store_b.resolve_access_token(access_token) is None


async def test_authorization_code_with_undecryptable_token_is_rejected(tmp_path):
    """Same key-mismatch scenario as access tokens, but for authorization codes."""
    import sqlite3
    from contextlib import closing

    store_a = LinkedAccountStore(
        db_path=tmp_path / "a.db", encryption_key=generate_encryption_key()
    )
    store_b = LinkedAccountStore(
        db_path=tmp_path / "b.db", encryption_key=generate_encryption_key()
    )

    code = await store_a.store_authorization_code(
        client_id="client-1",
        redirect_uri="https://claude.ai/api/mcp/auth_callback",
        code_challenge="abc123",
        datawrapper_token="dw-secret-token",
    )

    with closing(sqlite3.connect(store_a._db_path)) as conn_a:
        row = conn_a.execute(
            "SELECT code, client_id, redirect_uri, code_challenge, encrypted_token, "
            "expires_at FROM authorization_codes WHERE code = ?",
            (code,),
        ).fetchone()
    with closing(sqlite3.connect(store_b._db_path)) as conn_b:
        conn_b.execute(
            "INSERT INTO authorization_codes "
            "(code, client_id, redirect_uri, code_challenge, encrypted_token, "
            "expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        conn_b.commit()

    assert await store_b.consume_authorization_code(code) is None
