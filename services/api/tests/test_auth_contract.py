"""Focused authentication boundary tests. Uses synthetic tokens only."""
import pytest
from fastapi import HTTPException
from app.core.security import create_access_token, create_refresh_token, decode_token

def test_access_and_refresh_tokens_have_distinct_types():
    access = decode_token(create_access_token("00000000-0000-4000-8000-000000000001", "patient", "synthetic-session"))
    refresh = decode_token(create_refresh_token("00000000-0000-4000-8000-000000000001", "synthetic-session"))
    assert access.type == "access"
    assert refresh.type == "refresh"
    assert access.session_id == refresh.session_id

def test_malformed_token_is_rejected():
    with pytest.raises(HTTPException) as exception:
        decode_token("malformed.token.value")
    assert exception.value.status_code == 401
