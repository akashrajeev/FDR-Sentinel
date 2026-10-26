"""Provision the local operator in an existing development realm without resetting users."""
import os
import time

import httpx
import psycopg

base = os.environ.get('IDP_ADMIN_URL', 'http://keycloak:8080')
for attempt in range(90):
    try:
        response = httpx.post(base + '/realms/master/protocol/openid-connect/token', data={
            'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'local-admin',
            'password': os.environ['KEYCLOAK_ADMIN_PASSWORD']}, timeout=5)
        if response.status_code == 200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(2)
else:
    raise RuntimeError('Local IdP administrator did not become ready')
headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
url = base + '/admin/realms/sentinel/users'
existing = httpx.get(url, headers=headers, params={'username': 'operator', 'exact': 'true'}, timeout=10)
existing.raise_for_status()
if not existing.json():
    created = httpx.post(url, headers=headers, timeout=15, json={
        'id': '10000000-0000-0000-0000-000000000009', 'username': 'operator', 'enabled': True,
        'emailVerified': True, 'email': 'operator@sentinel.invalid', 'firstName': 'Synthetic', 'lastName': 'Operator',
        'credentials': [{'type': 'password', 'value': os.environ['DEMO_OPERATOR_PASSWORD'], 'temporary': False}]})
    created.raise_for_status()
print('Local operator identity exists; existing accounts and credentials preserved.')
actual = httpx.get(url, headers=headers, params={'username': 'operator', 'exact': 'true'}, timeout=10)
actual.raise_for_status()
subject = actual.json()[0]['id']
with psycopg.connect(os.environ['OPERATOR_DATABASE_DSN']) as db:
    db.execute('INSERT INTO principals(subject,enabled) VALUES (%s,true) ON CONFLICT DO NOTHING', (subject,))
    db.execute("INSERT INTO role_bindings(id,subject,role,scope_type,scope_id,enabled,valid_from) "
               "VALUES (gen_random_uuid()::text,%s,'OPERATOR','BUREAU','PLATFORM',true,now()) "
               "ON CONFLICT (subject,role,scope_type,scope_id) DO NOTHING", (subject,))
print('Actual IdP subject provisioned with technical operator scope; no financial permissions.')
