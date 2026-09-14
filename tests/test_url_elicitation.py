"""Tests for the URL-mode elicitation login prototype."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import ElicitResult
from starlette.testclient import TestClient

from datawrapper_mcp import url_elicitation


@pytest.fixture(autouse=True)
def _clean_pending_store():
    url_elicitation._pending.clear()
    yield
    url_elicitation._pending.clear()


@pytest.fixture(autouse=True)
def _reset_sidecar_server():
    url_elicitation._server = None
    yield
    url_elicitation._server = None


@pytest.fixture
def connect_client():
    return TestClient(url_elicitation.build_connect_app())


@pytest.fixture
def mock_datawrapper_client():
    with patch("datawrapper_mcp.url_elicitation.Datawrapper") as mock_class:
        client = MagicMock()
        mock_class.return_value = client
        yield mock_class, client


# ---------------------------------------------------------------------------
# Pending-connect store
# ---------------------------------------------------------------------------


async def test_create_pending_connect_is_unverified_and_unique():
    first = await url_elicitation.create_pending_connect()
    second = await url_elicitation.create_pending_connect()

    assert first != second
    pending = await url_elicitation.get_pending_connect(first)
    assert pending is not None
    assert pending.verified is False
    assert pending.account is None


async def test_get_pending_connect_unknown_id_returns_none():
    assert await url_elicitation.get_pending_connect("does-not-exist") is None


async def test_expired_pending_connects_are_swept():
    connect_id = await url_elicitation.create_pending_connect()
    url_elicitation._pending[connect_id].created_at -= (
        url_elicitation.PENDING_TTL_SECONDS + 1
    )

    # The sweep runs as a side effect of registering a new one.
    await url_elicitation.create_pending_connect()

    assert await url_elicitation.get_pending_connect(connect_id) is None


# ---------------------------------------------------------------------------
# /connect/<id> HTTP handlers
# ---------------------------------------------------------------------------


class TestConnectPage:
    async def test_get_unknown_id_is_404(self, connect_client):
        response = connect_client.get("/connect/nope")

        assert response.status_code == 404
        assert "expired" in response.text

    async def test_get_pending_shows_form(self, connect_client):
        connect_id = await url_elicitation.create_pending_connect()

        response = connect_client.get(f"/connect/{connect_id}")

        assert response.status_code == 200
        assert "<form" in response.text
        assert "api-tokens" in response.text

    async def test_get_after_verified_shows_success(self, connect_client):
        connect_id = await url_elicitation.create_pending_connect()
        url_elicitation._pending[connect_id].verified = True
        url_elicitation._pending[connect_id].account = {"email": "ben@example.com"}

        response = connect_client.get(f"/connect/{connect_id}")

        assert response.status_code == 200
        assert "ben@example.com" in response.text

    async def test_post_unknown_id_is_404(self, connect_client):
        response = connect_client.post("/connect/nope", data={"access_token": "tok"})

        assert response.status_code == 404

    async def test_post_blank_token_reprompts(self, connect_client):
        connect_id = await url_elicitation.create_pending_connect()

        response = connect_client.post(f"/connect/{connect_id}", data={})

        assert response.status_code == 200
        assert "paste a token" in response.text
        pending = await url_elicitation.get_pending_connect(connect_id)
        assert pending is not None
        assert pending.verified is False

    async def test_post_invalid_token_reprompts_without_verifying(
        self, connect_client, mock_datawrapper_client
    ):
        _mock_class, client = mock_datawrapper_client
        client.get_my_account.side_effect = Exception("401 Unauthorized")
        connect_id = await url_elicitation.create_pending_connect()

        response = connect_client.post(
            f"/connect/{connect_id}", data={"access_token": "bad-token"}
        )

        assert response.status_code == 200
        assert "rejected" in response.text
        pending = await url_elicitation.get_pending_connect(connect_id)
        assert pending is not None
        assert pending.verified is False

    async def test_post_valid_token_verifies_and_shows_success(
        self, connect_client, mock_datawrapper_client
    ):
        mock_class, client = mock_datawrapper_client
        client.get_my_account.return_value = {
            "id": 42,
            "email": "ben@example.com",
            "name": "Ben",
        }
        connect_id = await url_elicitation.create_pending_connect()

        response = connect_client.post(
            f"/connect/{connect_id}", data={"access_token": "good-token"}
        )

        assert response.status_code == 200
        assert "Connected" in response.text
        mock_class.assert_called_once_with(access_token="good-token")

        pending = await url_elicitation.get_pending_connect(connect_id)
        assert pending is not None
        assert pending.verified is True
        assert pending.account == {"email": "ben@example.com", "name": "Ben", "id": 42}


# ---------------------------------------------------------------------------
# login_guard - the multi-round-trip state machine
# ---------------------------------------------------------------------------


class TestLoginGuard:
    async def test_first_round_asks_via_url_mode(self, monkeypatch):
        monkeypatch.setenv("DATAWRAPPER_MCP_CONNECT_URL", "https://mcp.example.com")

        result = await url_elicitation.login_guard(None, None)

        assert isinstance(result, type(result))  # InputRequiredResult
        ask = result.input_requests["connect"]
        assert ask.params.mode == "url"
        assert ask.params.url.startswith("https://mcp.example.com/connect/")
        assert result.request_state is not None
        # The connect id in the URL matches what was registered.
        connect_id = ask.params.url.rsplit("/", 1)[-1]
        pending = await url_elicitation.get_pending_connect(connect_id)
        assert pending is not None

    async def test_decline_returns_plain_message(self):
        result = await url_elicitation.login_guard(
            {"connect": ElicitResult(action="decline")}, "some-id"
        )

        assert isinstance(result, str)
        assert "declined" in result

    async def test_cancel_returns_plain_message(self):
        result = await url_elicitation.login_guard(
            {"connect": ElicitResult(action="cancel")}, "some-id"
        )

        assert isinstance(result, str)
        assert "dismissed" in result

    async def test_missing_response_asks_to_try_again(self):
        result = await url_elicitation.login_guard({}, "some-id")

        assert (
            result == "Didn't receive a response to the connection prompt. Try again."
        )

    async def test_accept_before_page_completed_reasks_same_link(self, monkeypatch):
        monkeypatch.setenv("DATAWRAPPER_MCP_CONNECT_URL", "https://mcp.example.com")
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_ROUNDS", 2)
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_INTERVAL", 0)
        connect_id = await url_elicitation.create_pending_connect()

        result = await url_elicitation.login_guard(
            {"connect": ElicitResult(action="accept")}, connect_id
        )

        ask = result.input_requests["connect"]
        assert ask.params.url == f"https://mcp.example.com/connect/{connect_id}"
        assert result.request_state == connect_id
        assert "waiting" in ask.params.message.lower()

    async def test_accept_after_page_completed_returns_account_json(self, monkeypatch):
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_ROUNDS", 2)
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_INTERVAL", 0)
        connect_id = await url_elicitation.create_pending_connect()
        url_elicitation._pending[connect_id].verified = True
        url_elicitation._pending[connect_id].account = {
            "email": "ben@example.com",
            "id": 1,
        }

        result = await url_elicitation.login_guard(
            {"connect": ElicitResult(action="accept")}, connect_id
        )

        assert isinstance(result, str)
        assert '"connected": true' in result
        assert "ben@example.com" in result

    async def test_accept_verified_partway_through_polling(self, monkeypatch):
        """Simulate the user finishing the page mid-poll, not immediately."""
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_ROUNDS", 5)
        monkeypatch.setattr(url_elicitation, "_CONNECT_POLL_INTERVAL", 0)
        connect_id = await url_elicitation.create_pending_connect()

        calls = {"n": 0}
        real_get = url_elicitation.get_pending_connect

        async def flaky_get(cid: str):
            calls["n"] += 1
            if calls["n"] >= 3:
                url_elicitation._pending[connect_id].verified = True
                url_elicitation._pending[connect_id].account = {
                    "email": "later@example.com"
                }
            return await real_get(cid)

        monkeypatch.setattr(url_elicitation, "get_pending_connect", flaky_get)

        result = await url_elicitation.login_guard(
            {"connect": ElicitResult(action="accept")}, connect_id
        )

        assert isinstance(result, str)
        assert "later@example.com" in result


# ---------------------------------------------------------------------------
# ensure_connect_server_url
# ---------------------------------------------------------------------------


class TestEnsureConnectServerUrl:
    async def test_honors_explicit_connect_url_without_starting_sidecar(
        self, monkeypatch
    ):
        monkeypatch.setenv("DATAWRAPPER_MCP_CONNECT_URL", "https://mcp.example.com/")

        url = await url_elicitation.ensure_connect_server_url()

        assert url == "https://mcp.example.com"
        assert url_elicitation._server is None

    async def test_starts_sidecar_once_when_no_override(self, monkeypatch):
        monkeypatch.delenv("DATAWRAPPER_MCP_CONNECT_URL", raising=False)
        monkeypatch.setenv("DATAWRAPPER_MCP_CONNECT_PORT", "18420")

        fake_server = MagicMock()
        fake_server.started = True
        fake_server.serve = AsyncMock()
        with patch(
            "datawrapper_mcp.url_elicitation.uvicorn.Server", return_value=fake_server
        ):
            first_url = await url_elicitation.ensure_connect_server_url()
            second_url = await url_elicitation.ensure_connect_server_url()

        assert first_url == "http://127.0.0.1:18420"
        assert second_url == "http://127.0.0.1:18420"
        assert url_elicitation._server is fake_server
