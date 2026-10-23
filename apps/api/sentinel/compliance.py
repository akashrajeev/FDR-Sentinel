"""Pure deterministic policy evaluation. No network, model or decision authority."""
import hashlib
import json
from importlib.resources import files

POLICY_BYTES = files('sentinel').joinpath('policies/aph-2024-27.v1.json').read_bytes()
POLICY = json.loads(POLICY_BYTES)
POLICY_REVISION = hashlib.sha256(POLICY_BYTES).hexdigest()
ALGORITHM = 'deterministic-aph-and-evidence-v1'


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def required_amount(context: dict, regulatory_event: str) -> int | None:
    if (context['academic_year'] not in POLICY['academic_years']
            or context['exceptional_context'] or regulatory_event != 'NEW_INSTITUTION'):
        return None
    if context['governance'] in ('GOVERNMENT', 'GOVERNMENT_AIDED'):
        return 0
    if (context['governance'] != 'PRIVATE' or context['programme'] != 'ENGINEERING_UG'
            or context['land'] not in ('OWNED', 'PRIVATE_LEASE')):
        return None
    return POLICY['engineering_ug_base_paise'] * (
        POLICY['private_lease_multiplier'] if context['land'] == 'PRIVATE_LEASE' else 1)


def document_set_hash(documents) -> str:
    return digest(sorted((d.id, d.sha256, d.status, digest(d.evidence)) for d in documents))


def evaluate(inputs: dict, documents: list) -> dict:
    expected = required_amount(inputs['context'], inputs['regulatory_event'])
    findings = []
    if expected is None:
        findings.append({'code': 'UNSUPPORTED_CONTEXT', 'severity': 'REVIEW',
                         'message': 'Policy scope or history requires human review', 'citation': POLICY['clause']})
    elif inputs['amount_paise'] < expected:
        findings.append({'code': 'UNDERFUNDED', 'severity': 'FAIL', 'asserted': inputs['amount_paise'],
                         'expected': expected, 'citation': POLICY['clause'],
                         'message': 'Declared amount is below the supported contextual obligation',
                         'evidence': [{'document_id': d.id, 'sha256': d.sha256, **e}
                                      for d in documents for e in d.evidence if e['field'] == 'amount_paise']})
    for doc in documents:
        for evidence in doc.evidence:
            field = evidence['field']
            if field in inputs and inputs[field] is not None and str(evidence['value']) != str(inputs[field]):
                findings.append({'code': 'DOCUMENT_MISMATCH', 'severity': 'FAIL', 'field': field,
                                 'message': f'Document {field} differs from declaration',
                                 'asserted': inputs[field], 'observed': evidence['value'],
                                 'evidence': {'document_id': doc.id, 'sha256': doc.sha256, **evidence},
                                 'citation': 'Product evidence consistency control, not statutory authenticity'})
    if not any(d.evidence for d in documents):
        findings.append({'code': 'EXTRACTION_UNAVAILABLE', 'severity': 'REVIEW',
                         'message': 'No supported digital fields; explicit human evidence review required'})
    findings.append({'code': 'PROVISIONAL_POLICY', 'severity': 'REVIEW',
                     'message': 'Source amendments and legal effectivity need policy-owner validation',
                     'citation': POLICY['source_url']})
    outcome = 'FAIL' if any(f['severity'] == 'FAIL' for f in findings) else 'REVIEW'
    return {'outcome': outcome, 'required_amount_paise': expected, 'findings': findings,
            'policy': POLICY, 'policy_revision': POLICY_REVISION, 'algorithm': ALGORITHM,
            'registration_only': True, 'release_eligible': False}
