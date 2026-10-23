"""Generate local-only credentials/IdP realm without overwriting existing secrets."""
import json
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = root / '.env'
local = root / '.local'
local.mkdir(exist_ok=True)
if env.exists():
    print('Existing .env retained. Remove explicitly only when resetting the entire local stack.')
    raise SystemExit(0)

names = ['institution', 'other-institution', 'reviewer', 'pgrc', 'vigilance', 'approver', 'issuer', 'auditor']
subjects = {name: f'10000000-0000-0000-0000-{index:012d}' for index, name in enumerate(names, 1)}
values = {key: secrets.token_hex(24) for key in (
    'POSTGRES_PASSWORD', 'S3_SECRET_KEY', 'REFERENCE_HMAC_KEY', 'KEYCLOAK_ADMIN_PASSWORD')}
values['S3_ACCESS_KEY'] = 'sentinel-' + secrets.token_hex(6)
values.update({f'DEMO_{name.upper().replace("-", "_")}_PASSWORD': secrets.token_urlsafe(18) for name in names})
env.write_text('\n'.join(f'{key}={value}' for key, value in values.items()) + '\n', encoding='utf-8')
audience = {'name': 'api-audience', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-audience-mapper',
            'consentRequired': False, 'config': {'included.client.audience': 'sentinel-api',
                                               'access.token.claim': 'true', 'id.token.claim': 'false'}}
realm = {
    'realm': 'sentinel', 'enabled': True, 'displayName': 'FDR Sentinel · Synthetic local environment',
    'registrationAllowed': False, 'resetPasswordAllowed': False,
    'bruteForceProtected': True, 'accessTokenLifespan': 300,
    'clients': [
        {'clientId': 'sentinel-api', 'enabled': True, 'bearerOnly': True},
        {'clientId': 'sentinel-web', 'publicClient': True, 'standardFlowEnabled': True,
         'directAccessGrantsEnabled': False,
         'redirectUris': ['http://localhost:8088/callback', 'http://localhost:5173/callback'],
         'webOrigins': ['http://localhost:8088', 'http://localhost:5173'],
         'attributes': {'pkce.code.challenge.method': 'S256',
                        'post.logout.redirect.uris': 'http://localhost:8088/*##http://localhost:5173/*'},
         'protocolMappers': [audience]},
        {'clientId': 'sentinel-tests', 'publicClient': True, 'standardFlowEnabled': False,
         'directAccessGrantsEnabled': True, 'protocolMappers': [audience]},
    ],
    'users': [{'id': subjects[name], 'username': name, 'enabled': True, 'emailVerified': True,
               'email': name + '@sentinel.invalid', 'firstName': 'Synthetic', 'lastName': name,
               'credentials': [{'type': 'password', 'value': values[
                   f'DEMO_{name.upper().replace("-", "_")}_PASSWORD'], 'temporary': False}]} for name in names],
}
(local / 'realm.json').write_text(json.dumps(realm, indent=2), encoding='utf-8')
(local / 'subjects.json').write_text(json.dumps(subjects, indent=2), encoding='utf-8')
print('Generated ignored .env and .local/realm.json. Credentials remain in .env; never commit them.')
