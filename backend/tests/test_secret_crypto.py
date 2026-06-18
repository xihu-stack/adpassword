import os
import pytest
from services import secret_crypto


def test_roundtrip():
    plain = 'P@ssw0rd-非常机密'
    token = secret_crypto.encrypt_value(plain)
    assert token != plain
    assert secret_crypto.decrypt_value(token) == plain


def test_decrypt_garbage_returns_none():
    assert secret_crypto.decrypt_value('not-a-valid-token') is None


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv('SECRET_ENCRYPTION_KEY', raising=False)
    with pytest.raises(RuntimeError):
        secret_crypto.encrypt_value('x')
