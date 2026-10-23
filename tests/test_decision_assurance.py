import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sentinel.auth import Actor, require_decision_assurance


def test_recent_verified_mfa_gate(monkeypatch):
    monkeypatch.setattr('sentinel.auth.settings', lambda: SimpleNamespace(
        decision_mfa_required=True, decision_auth_max_age_seconds=300))
    now = int(time.time())
    for actor in (Actor('synthetic', ()), Actor('synthetic', (), ('pwd',), now),
                  Actor('synthetic', (), ('otp',), now - 301), Actor('synthetic', (), ('otp',), now + 60)):
        with pytest.raises(HTTPException) as error:
            require_decision_assurance(actor)
        assert error.value.status_code == 403
    require_decision_assurance(Actor('synthetic', (), ('pwd', 'otp'), now))


def test_synthetic_mfa_exemption_is_explicit(monkeypatch):
    monkeypatch.setattr('sentinel.auth.settings', lambda: SimpleNamespace(decision_mfa_required=False))
    require_decision_assurance(Actor('synthetic', ()))
