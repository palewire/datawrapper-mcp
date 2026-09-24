"""Tests for PKCE S256 verification."""

import base64
import hashlib

from datawrapper_mcp.oauth.pkce import verify_code_challenge


def _challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def test_matching_verifier_and_challenge_succeed():
    verifier = "a-random-code-verifier-that-is-long-enough"
    challenge = _challenge_for(verifier)

    assert (
        verify_code_challenge(code_verifier=verifier, code_challenge=challenge) is True
    )


def test_mismatched_verifier_fails():
    challenge = _challenge_for("the-real-verifier")

    assert (
        verify_code_challenge(
            code_verifier="a-different-verifier", code_challenge=challenge
        )
        is False
    )


def test_empty_verifier_fails():
    challenge = _challenge_for("the-real-verifier")

    assert verify_code_challenge(code_verifier="", code_challenge=challenge) is False
