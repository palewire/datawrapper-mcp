"""Tests for the check_datawrapper_connection handler."""

from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.whoami import check_datawrapper_connection


@pytest.fixture
def mock_datawrapper_client():
    with patch("datawrapper_mcp.handlers.whoami.Datawrapper") as mock_class:
        client = MagicMock()
        mock_class.return_value = client
        yield mock_class, client


async def test_reports_authenticated_account(mock_datawrapper_client):
    mock_class, client = mock_datawrapper_client
    client.get_my_account.return_value = {
        "id": 42,
        "email": "ben@example.com",
        "name": "Ben",
    }

    result = await check_datawrapper_connection({"access_token": "explicit-token"})

    assert '"email": "ben@example.com"' in result[0].text
    assert '"name": "Ben"' in result[0].text
    assert '"id": 42' in result[0].text
    assert '"connected": true' in result[0].text
    mock_class.assert_called_once_with(access_token="explicit-token")


async def test_falls_back_to_env_var_when_no_token_given(
    mock_datawrapper_client, monkeypatch
):
    mock_class, client = mock_datawrapper_client
    client.get_my_account.return_value = {"id": 1, "email": "env@example.com"}
    monkeypatch.setenv("DATAWRAPPER_ACCESS_TOKEN", "env-token")

    await check_datawrapper_connection({})

    # Never construct Datawrapper(access_token=None) - that would send a
    # literal "Bearer None" request instead of falling back correctly.
    mock_class.assert_called_once_with(access_token="env-token")


async def test_normalizes_empty_string_token(mock_datawrapper_client, monkeypatch):
    mock_class, client = mock_datawrapper_client
    client.get_my_account.return_value = {"id": 1, "email": "env@example.com"}
    monkeypatch.setenv("DATAWRAPPER_ACCESS_TOKEN", "env-token")

    await check_datawrapper_connection({"access_token": ""})

    mock_class.assert_called_once_with(access_token="env-token")


async def test_no_token_anywhere_passes_none(mock_datawrapper_client, monkeypatch):
    mock_class, client = mock_datawrapper_client
    client.get_my_account.return_value = {"id": 1, "email": "e@example.com"}
    monkeypatch.delenv("DATAWRAPPER_ACCESS_TOKEN", raising=False)

    await check_datawrapper_connection({})

    mock_class.assert_called_once_with(access_token=None)


async def test_401_raises_troubleshooting_guidance(mock_datawrapper_client):
    _mock_class, client = mock_datawrapper_client
    client.get_my_account.side_effect = Exception(
        "Request failed with status code 401. Response content: b'Unauthorized'"
    )

    with pytest.raises(ValueError, match="rejected this token") as exc_info:
        await check_datawrapper_connection({"access_token": "bad-token"})

    message = str(exc_info.value)
    assert "Bearer" in message
    assert "Required" in message
    assert "api-tokens" in message


async def test_403_raises_troubleshooting_guidance(mock_datawrapper_client):
    _mock_class, client = mock_datawrapper_client
    client.get_my_account.side_effect = Exception(
        "Request failed with status code 403. Response content: b'Forbidden'"
    )

    with pytest.raises(ValueError, match="rejected this token"):
        await check_datawrapper_connection({"access_token": "bad-token"})


async def test_other_failure_raises_generic_guidance(mock_datawrapper_client):
    _mock_class, client = mock_datawrapper_client
    client.get_my_account.side_effect = Exception("connection reset by peer")

    with pytest.raises(ValueError, match="Could not reach Datawrapper") as exc_info:
        await check_datawrapper_connection({"access_token": "some-token"})

    assert "connection reset by peer" in str(exc_info.value)
