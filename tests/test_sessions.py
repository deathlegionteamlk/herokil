"""
Tests for herokil.sessions - Secure cookie sessions.
"""

import pytest
from herokil.sessions import SecureCookieSession, SecureCookieSessionInterface


class TestSecureCookieSession:
    """Tests for the SecureCookieSession dict subclass."""

    def test_create_empty(self):
        """Empty sessions can be created."""
        s = SecureCookieSession()
        assert len(s) == 0
        assert s.modified is False

    def test_create_with_data(self):
        """Sessions can be created with initial data."""
        s = SecureCookieSession({"user": "alice"})
        assert s["user"] == "alice"

    def test_setitem_marks_modified(self):
        """Setting a key marks the session as modified."""
        s = SecureCookieSession()
        s["key"] = "value"
        assert s.modified is True

    def test_delitem_marks_modified(self):
        """Deleting a key marks the session as modified."""
        s = SecureCookieSession({"key": "value"})
        s.modified = False
        del s["key"]
        assert s.modified is True

    def test_pop_marks_modified(self):
        """Popping a key marks the session as modified."""
        s = SecureCookieSession({"key": "value"})
        s.modified = False
        s.pop("key")
        assert s.modified is True

    def test_update_marks_modified(self):
        """Updating the session marks it as modified."""
        s = SecureCookieSession()
        s.update({"a": 1, "b": 2})
        assert s.modified is True

    def test_clear_marks_modified(self):
        """Clearing the session marks it as modified."""
        s = SecureCookieSession({"key": "value"})
        s.modified = False
        s.clear()
        assert s.modified is True


class TestSecureCookieSessionInterface:
    """Tests for the secure cookie session interface."""

    def test_encode_decode_roundtrip(self):
        """Session data survives an encode/decode roundtrip."""
        iface = SecureCookieSessionInterface()
        secret = "supersecretkey123"
        data = {"user": "alice", "role": "admin"}

        encoded = iface._encode(data, secret)
        decoded = iface._decode(encoded, secret)
        assert decoded == data

    def test_decode_tampered_fails(self):
        """Tampered session cookies fail to decode."""
        iface = SecureCookieSessionInterface()
        secret = "supersecretkey123"
        data = {"user": "alice"}

        encoded = iface._encode(data, secret)
        # Tamper with the value
        tampered = encoded + "x"
        decoded = iface._decode(tampered, secret)
        assert decoded is None

    def test_decode_wrong_secret_fails(self):
        """Cookies signed with a different secret fail to decode."""
        iface = SecureCookieSessionInterface()
        data = {"user": "alice"}
        encoded = iface._encode(data, "secret1")
        decoded = iface._decode(encoded, "secret2")
        assert decoded is None

    def test_decode_malformed_fails(self):
        """Malformed cookie values return None."""
        iface = SecureCookieSessionInterface()
        assert iface._decode("not-a-valid-cookie", "secret") is None
        assert iface._decode("", "secret") is None
