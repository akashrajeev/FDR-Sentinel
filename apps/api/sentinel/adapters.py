"""Explicit external-source ports. Only a signed, synthetic fixture adapter is enabled."""
import hashlib
import hmac
import json
from typing import Protocol

from sentinel.config import settings
from sentinel.models import now


class BankVerificationPort(Protocol):
    def request_verification(self, record_id: str, requested_fields: dict, idempotency_key: str) -> dict: ...


class MockBankAdapter:
    def request_verification(self, record_id: str, requested_fields: dict, idempotency_key: str,
                             scenario='MATCH') -> dict:
        config = settings()
        if not config.synthetic_mode or config.environment != 'development':
            raise RuntimeError('Simulated adapters are forbidden outside the local synthetic environment')
        if len(config.mock_attestation_key) < 32:
            raise RuntimeError('Run bootstrap to provision a local demo signing key')
        observed = dict(requested_fields)
        if scenario == 'AMOUNT_MISMATCH':
            observed['amount_paise'] = 1000000
        payload = {'source': 'SIMULATED_BANK_FIXTURE', 'fixture_version': 'synthetic-bank-v1',
                   'record_id': record_id, 'correlation_id': idempotency_key, 'scenario': scenario,
                   'observed': None if scenario == 'UNAVAILABLE' else observed,
                   'authenticity': 'SIMULATED_NOT_BANK_CONFIRMED', 'created_at': now().isoformat(),
                   'note': 'MATCH is a synthetic echo scenario, not independent bank verification'}
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        signature = hmac.new(config.mock_attestation_key.encode(), serialized, hashlib.sha256).hexdigest()
        return {'payload': payload, 'signature': signature,
                'outcome': 'SIMULATED_' + scenario, 'signature_type': 'LOCAL_DEMO_HMAC_NOT_BANK_PKI'}


class AuthorizedBankAPIAdapter:
    def request_verification(self, record_id: str, requested_fields: dict, idempotency_key: str) -> dict:
        raise RuntimeError('No authorized bank integration is configured; written authorization is required')


class AICTERegistryAdapter:
    def lookup(self, institution_id: str) -> dict:
        return {'status': 'NOT_CONNECTED', 'institution_id': institution_id,
                'note': 'Declaration does not constitute AICTE registry confirmation'}
