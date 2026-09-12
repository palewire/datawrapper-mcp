"""PKCE (RFC 7636) verification, S256 method only."""

import base64
import hashlib


def verify_code_challenge(*, code_verifier: str, code_challenge: str) -> bool:
    """Check a token request's code_verifier against the stored S256 challenge."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return computed == code_challenge
