import os
import re
import time
from pathlib import Path
from uuid import uuid4

import pytest
from conftest import pdf_bytes
from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.browser


def login(page, username):
    page.goto('http://localhost:8088')
    page.get_by_role('button', name='Sign in securely').click()
    page.get_by_label('Username or email').fill(username)
    page.get_by_label('Password', exact=True).fill(os.environ[f'DEMO_{username.upper().replace("-", "_")}_PASSWORD'])
    page.get_by_role('button', name='Sign In', exact=True).click()
    expect(page.get_by_role('heading', name='Your operations, at a glance.')).to_be_visible(timeout=30000)


def test_browser_real_pkce_and_worker_to_officer():
    output = Path('.local/browser')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        maker_context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = maker_context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, 'institution')
        page.get_by_role('button', name='+ Register deposit').click()
        page.get_by_label('Full reference').fill('SYN-BROWSER-' + uuid4().hex)
        page.get_by_label('Obligation / institution', exact=True).select_option('30000000-0000-0000-0000-000000000001')
        page.get_by_label('Declared amount (INR)').fill('3500000')
        page.get_by_label('Issue date', exact=True).fill('2016-10-01')
        page.get_by_label('Maturity date', exact=True).fill('2026-10-01')
        with page.expect_response(lambda response: response.url.endswith('/api/v1/deposits')
                                  and response.request.method == 'POST') as response:
            page.get_by_role('button', name='Save deposit').click()
        record = response.value.json()
        page.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        page.get_by_label('PDF file').set_input_files({'name': 'synthetic.pdf', 'mimeType': 'application/pdf',
                                                      'buffer': pdf_bytes()})
        page.get_by_role('button', name='Upload privately').click()
        expect(page.get_by_text('READY', exact=True)).to_be_visible(timeout=60000)
        page.get_by_role('button', name='Run current evaluation').click()
        expect(page.get_by_text('PROVISIONAL POLICY', exact=True)).to_be_visible(timeout=15000)
        page.get_by_role('button', name='Submit for scrutiny').click()
        expect(page.get_by_text('PENDING SCRUTINY', exact=True)).to_be_visible(timeout=15000)
        page.screenshot(path=str(output / 'submission.png'), full_page=True)
        officer_context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        officer = officer_context.new_page()
        officer.on('pageerror', lambda error: errors.append(str(error)))
        login(officer, 'reviewer')
        officer.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        officer.get_by_label('Officer decision').select_option('ACCEPT_REGISTRATION')
        officer.get_by_label('Reason / correction request').fill('Original synthetic evidence inspected; registration only, no bank confirmation.')
        officer.get_by_role('checkbox').check()
        officer.get_by_role('button', name='Record human decision').click()
        expect(officer.get_by_text('MANUALLY REVIEWED', exact=True)).to_be_visible(timeout=15000)
        officer.screenshot(path=str(output / 'officer-review.png'), full_page=True)
        assert not errors, errors
        browser.close()


def test_browser_pgrc_block_to_independent_synthetic_issuance():
    eligible = accepted_fixture()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        def desk(username):
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            page = context.new_page()
            login(page, username)
            page.get_by_role('button', name='Release cases').first.click()
            return page
        maker = desk('institution')
        maker.get_by_label('Accepted deposit', exact=True).select_option(eligible['id'])
        with maker.expect_response(lambda r: r.url.endswith('/api/v1/release-cases')
                                   and r.request.method == 'POST') as response:
            maker.get_by_role('button', name='Create release case', exact=True).click()
        assert response.value.status == 200
        case = response.value.json()
        for category in ('REQUEST_LETTER', 'AFFIDAVIT_6', 'APPROVAL_LETTER'):
            maker.get_by_label('Release evidence category').select_option(category)
            maker.get_by_label('Release PDF', exact=True).set_input_files({
                'name': category + '.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes()})
            with maker.expect_response(lambda r: r.url.endswith(f"/release-cases/{case['id']}/documents")
                                       and r.request.method == 'POST') as uploaded:
                maker.get_by_role('button', name='Upload release evidence', exact=True).click()
            assert uploaded.value.status == 200
            expect(maker.get_by_role('button', name='Upload release evidence', exact=True)).to_be_enabled()
        expect(maker.get_by_text('READY', exact=True)).to_have_count(4, timeout=60000)
        maker.get_by_role('button', name='Submit to bureaus', exact=True).click()
        expect(maker.get_by_text('Human action committed with audit evidence.', exact=True)).to_be_visible()

        def open_case(username):
            page = desk(username)
            page.get_by_text(case['id'][:8].upper(), exact=True).click()
            return page

        for username, bureau in [('vigilance', 'VIGILANCE'), ('reviewer', 'GRANTS')]:
            page = open_case(username)
            page.get_by_label(bureau + ' reason', exact=True).fill('Synthetic bureau evidence reviewed and cleared by scoped human.')
            page.get_by_role('button', name=f'Record {bureau} decision', exact=True).click()
            expect(page.get_by_text('CLEARED', exact=True)).to_have_count(1 if bureau == 'VIGILANCE' else 2)

        approver = open_case('approver')
        approver.get_by_label('Independent approver regulatory basis').fill(
            'Synthetic applicability and term reviewed with all required evidence; provisional policy, no financial authority.')
        approver.get_by_role('checkbox').check()
        approver.get_by_role('button', name='Attempt synthetic approval', exact=True).click()
        expect(approver.get_by_role('alert')).to_contain_text('PGRC')
        approver.screenshot(path='.local/browser/pgrc-blocked.png', full_page=True)
        pgrc = open_case('pgrc')
        pgrc.get_by_label('PGRC reason', exact=True).fill('Synthetic PGRC grievance evidence inspected and cleared.')
        pgrc.get_by_role('button', name='Record PGRC decision', exact=True).click()
        expect(approver.get_by_text('Release is blocked', exact=True)).not_to_be_visible(timeout=15000)
        approver.get_by_role('button', name='Attempt synthetic approval', exact=True).click()
        expect(approver.get_by_role('button', name='Attempt synthetic approval', exact=True)).not_to_be_visible()
        issuer = open_case('issuer')
        issuer.get_by_role('button', name='Issue synthetic NOC', exact=True).click()
        expect(issuer.get_by_role('heading', name='Synthetic result issued')).to_be_visible(timeout=15000)
        from test_sandbox_integrations import fixture_ledger
        with portal_client('institution') as client:
            deposit = client.get('/deposits/' + case['deposit_id']).json()
        ledger = fixture_ledger(deposit)
        issuer.get_by_label('Independent bank ledger ID', exact=True).fill(ledger)
        issuer.get_by_role('button', name='Send case to AICTE sandbox', exact=True).click()
        expect(issuer.get_by_text('CASE_RECEIVED', exact=True)).to_be_visible(timeout=45000)
        issuer.get_by_role('button', name='Reconcile with bank sandbox', exact=True).click()
        expect(issuer.get_by_text('SANDBOX_COMPLETED', exact=True)).to_be_visible(timeout=45000)
        issuer.screenshot(path='.local/browser/synthetic-issued.png', full_page=True)
        browser.close()


def portal_client(username):
    import httpx
    response = httpx.post(os.environ['TEST_OIDC_URL'], data={'client_id': 'sentinel-tests',
        'grant_type': 'password', 'username': username,
        'password': os.environ['DEMO_' + username.upper().replace('-', '_') + '_PASSWORD']}, timeout=20)
    response.raise_for_status()
    return httpx.Client(base_url='http://127.0.0.1:8088/api/v1',
                        headers={'Authorization': 'Bearer ' + response.json()['access_token']}, timeout=20)


def api_command(client, path, body):
    response = client.post(path, json=body, headers={'Idempotency-Key': str(uuid4())})
    assert response.status_code == 200, response.text
    return response.json()


def accepted_fixture(issue='2016-10-01', maturity='2026-10-01'):
    # Scenario setup through real APIs; no SQL writes or fake officer service responses.
    with portal_client('institution') as maker, portal_client('reviewer') as reviewer:
        deposit = api_command(maker, '/deposits', {'obligation_id': '30000000-0000-0000-0000-000000000001',
            'deposit_type': 'FDR', 'bank_code': 'SYN-BANK', 'reference': 'SYN-BROWSER-' + uuid4().hex,
            'amount_paise': 350000000, 'issue_date': issue, 'maturity_date': maturity})
        uploaded = maker.post(f"/deposits/{deposit['id']}/documents", files={
            'file': ('synthetic.pdf', pdf_bytes(issue=issue, maturity=maturity), 'application/pdf')},
            headers={'Idempotency-Key': str(uuid4())})
        assert uploaded.status_code == 200
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            deposit = maker.get('/deposits/' + deposit['id']).json()
            if deposit['documents'][0]['status'] == 'READY':
                break
            time.sleep(1)
        assert deposit['documents'][0]['status'] == 'READY'
        api_command(maker, f"/deposits/{deposit['id']}/evaluate", {'expected_version': deposit['version']})
        deposit = maker.get('/deposits/' + deposit['id']).json()
        deposit = api_command(maker, f"/deposits/{deposit['id']}/submit", {'expected_version': deposit['version']})
        api_command(reviewer, f"/deposits/{deposit['id']}/review", {'expected_version': deposit['version'],
            'decision': 'ACCEPT_REGISTRATION', 'evidence_reviewed': True,
            'reason': 'Automated synthetic browser scenario setup; no genuine institutional approval.'})
        return maker.get('/deposits/' + deposit['id']).json()


def test_browser_new_onboarding_operator_assignment_registry_and_csv():
    import httpx
    from sentinel.config import settings
    from test_operator_import_delivery import csv_data
    external = 'SYNTHETIC-' + uuid4().hex
    legal_name = 'Fictional Browser Onboarding ' + uuid4().hex[:8]
    seeded = httpx.post(settings().sandbox_url + '/v1/fixtures/registry', timeout=10,
        headers={'Authorization': 'Bearer ' + os.environ['SANDBOX_ADMIN_KEY']}, json={
            'id': external, 'legal_name': legal_name, 'programme': 'ENGINEERING', 'governance': 'PRIVATE',
            'approval_from': '2024-07-01', 'approval_until': '2027-06-30', 'approval_status': 'ACTIVE'})
    assert seeded.status_code == 200
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        maker = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(maker, 'institution')
        maker.get_by_role('button', name='+ Onboard institution').click()
        maker.get_by_label('Legal name', exact=True).fill(legal_name)
        maker.get_by_label('Institution identifier (synthetic)', exact=True).fill(external)
        maker.get_by_label('Exceptional history / uncertainty', exact=True).select_option('no')
        with maker.expect_response(lambda r: r.url.endswith('/api/v1/obligations') and r.request.method == 'POST') as created:
            maker.get_by_role('button', name='Create institution & obligation', exact=True).click()
        obligation = created.value.json()
        institution = obligation['institution_id']
        card = maker.locator('section.panel').filter(has=maker.get_by_role('heading', name=legal_name, exact=True))
        card.get_by_role('button', name='Check sandbox institution registry', exact=True).click()
        expect(card.get_by_text('MATCH', exact=True)).to_be_visible(timeout=45000)
        operator = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(operator, 'operator')
        operator.get_by_role('button', name='⚙ Operator', exact=True).click()
        operator.get_by_label('Officer principal', exact=True).select_option('10000000-0000-0000-0000-000000000003')
        operator.get_by_label('Assigned scope', exact=True).select_option(institution)
        operator.get_by_label('Assignment reason', exact=True).fill('Assign independent reviewer to fictional browser onboarding.')
        operator.get_by_role('button', name='Assign scoped officer', exact=True).click()
        expect(operator.get_by_role('status')).to_contain_text('committed')
        operator.screenshot(path='.local/browser/operator-assignment.png', full_page=True)
        maker.get_by_role('button', name='⇧ Legacy import', exact=True).click()
        data = csv_data([{'obligation_id': obligation['id']}])
        maker.get_by_label('Legacy CSV file', exact=True).set_input_files({'name': 'fictional.csv', 'mimeType': 'text/csv', 'buffer': data})
        maker.get_by_role('button', name='Validate import preview', exact=True).click()
        expect(maker.get_by_role('heading', name='Import preview', exact=True)).to_be_visible()
        maker.get_by_role('button', name='Commit validated DRAFT records', exact=True).click()
        expect(maker.get_by_role('status')).to_contain_text('DRAFT records imported atomically')
        maker.screenshot(path='.local/browser/legacy-import.png', full_page=True)
        reviewer = browser.new_context(viewport={'width': 1440, 'height': 1000}).new_page()
        login(reviewer, 'reviewer')
        reviewer.get_by_role('button', name='Institutions', exact=False).first.click()
        expect(reviewer.get_by_role('heading', name=legal_name, exact=True)).to_be_visible()
        browser.close()


def test_browser_maturity_email_and_independent_renewal_lineage():
    old = accepted_fixture()
    new = accepted_fixture('2026-10-02', '2036-10-02')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        reviewer = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(reviewer, 'reviewer')
        reviewer.get_by_role('button', name='Release cases', exact=False).first.click()
        reviewer.get_by_label('Filter reminders by deposit ID', exact=True).fill(old['id'])
        reviewer.get_by_label('Synthetic demo clock override (optional)', exact=True).fill('2026-09-24')
        with reviewer.expect_response(lambda r: r.url.endswith('/api/v1/monitoring/run') and r.request.method == 'POST') as response:
            reviewer.get_by_role('button', name='Run maturity monitor', exact=True).click()
        assert response.value.status == 200
        expect(reviewer.get_by_text(re.compile('Email: SENT'))).to_be_visible(timeout=60000)
        reviewer.screenshot(path='.local/browser/maturity-email.png', full_page=True)
        maker = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(maker, 'institution')
        maker.get_by_role('button', name='Release cases', exact=False).first.click()
        maker.get_by_label('Original deposit', exact=True).select_option(old['id'])
        maker.get_by_label('New accepted deposit', exact=True).select_option(new['id'])
        maker.get_by_label('Relationship', exact=True).select_option('RENEWAL')
        maker.get_by_label('Evidence rationale', exact=True).fill('Later fictional deposit proof retains principal and documents the renewal lineage.')
        with maker.expect_response(lambda r: r.url.endswith('/api/v1/replacements') and r.request.method == 'POST') as requested:
            maker.get_by_role('button', name='Request lineage authorization', exact=True).click()
        assert requested.value.status == 200
        row = reviewer.locator('div.document').filter(has=reviewer.get_by_text(f"{old['id'][:8].upper()} → {new['id'][:8].upper()} · RENEWAL", exact=True))
        expect(row).to_be_visible(timeout=15000)
        row.get_by_label('Officer policy basis', exact=True).fill('Independent synthetic renewal review of later evidence and preserved principal; no real financial authority.')
        row.get_by_role('button', name='Authorize replacement', exact=True).click()
        expect(row.get_by_text('AUTHORIZED', exact=True)).to_be_visible(timeout=15000)
        reviewer.screenshot(path='.local/browser/renewal-lineage.png', full_page=True)
        with portal_client('institution') as client:
            assert client.get('/deposits/' + old['id']).json()['lifecycle_status'] == 'REPLACED'
        browser.close()


def test_browser_deficient_scrutiny_return_correction_and_tenant_isolation():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        maker = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(maker, 'institution')
        maker.get_by_role('button', name='+ Register deposit').click()
        maker.get_by_label('Full reference').fill('SYN-DEFICIENT-' + uuid4().hex)
        maker.get_by_label('Obligation / institution', exact=True).select_option('30000000-0000-0000-0000-000000000001')
        maker.get_by_label('Declared amount (INR)').fill('3000000')
        maker.get_by_label('Issue date', exact=True).fill('2016-10-01')
        maker.get_by_label('Maturity date', exact=True).fill('2026-10-01')
        with maker.expect_response(lambda r: r.url.endswith('/api/v1/deposits') and r.request.method == 'POST') as created:
            maker.get_by_role('button', name='Save deposit').click()
        record = created.value.json()
        maker.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        maker.get_by_label('PDF file').set_input_files({'name': 'underfunded.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes(300000000)})
        maker.get_by_role('button', name='Upload privately').click()
        expect(maker.get_by_text('READY', exact=True)).to_be_visible(timeout=90000)
        maker.get_by_role('button', name='Run current evaluation').click()
        maker.get_by_role('button', name='Submit for scrutiny').click()
        expect(maker.get_by_text('PENDING SCRUTINY', exact=True)).to_be_visible()
        officer = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(officer, 'reviewer')
        officer.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        officer.get_by_label('Officer decision').select_option('ACCEPT_REGISTRATION')
        officer.get_by_label('Reason / correction request').fill('Underfunded synthetic source inspected; attempt must remain blocked.')
        officer.get_by_role('checkbox').check()
        officer.get_by_role('button', name='Record human decision').click()
        expect(officer.get_by_role('alert')).to_contain_text('blockers')
        officer.get_by_label('Officer decision').select_option('RETURN')
        officer.get_by_label('Reason / correction request').fill('Return the deficient synthetic declaration for corrected amount and supporting proof.')
        officer.get_by_role('button', name='Record human decision').click()
        expect(maker.get_by_role('button', name='Save correction', exact=True)).to_be_visible(timeout=15000)
        maker.get_by_label('Amount (INR)', exact=True).fill('3500000')
        maker.get_by_role('button', name='Save correction', exact=True).click()
        with portal_client('institution') as client:
            original = client.get('/deposits/' + record['id']).json()['documents'][0]['id']
        maker.get_by_label('Supersede previous evidence (optional)', exact=True).select_option(original)
        maker.get_by_label('PDF file').set_input_files({'name': 'corrected.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes()})
        with maker.expect_response(lambda r: r.url.endswith(f"/deposits/{record['id']}/documents") and r.request.method == 'POST') as replacement_upload:
            maker.get_by_role('button', name='Upload privately').click()
        proof = maker.locator('div.document').filter(has_text=replacement_upload.value.json()['sha256'])
        expect(proof.get_by_text('READY', exact=True)).to_be_visible(timeout=90000)
        expect(maker.get_by_text('SUPERSEDED', exact=True)).to_be_visible()
        maker.get_by_role('button', name='Run current evaluation').click()
        maker.get_by_role('button', name='Submit for scrutiny').click()
        expect(officer.get_by_label('Discrepancy resolution reason', exact=True)).to_be_visible(timeout=15000)
        with portal_client('institution') as client:
            current = client.get('/deposits/' + record['id']).json()
            replacement_proof = next(d['id'] for d in current['documents'] if d['active'])
        officer.get_by_label('Resolution evidence').select_option(replacement_proof)
        officer.get_by_label('Discrepancy resolution reason', exact=True).fill('Corrected independent proof and current evaluation remove the previously recorded amount blocker.')
        officer.get_by_role('button', name='Resolve corrected discrepancy', exact=True).click()
        officer.get_by_label('Officer decision').select_option('ACCEPT_REGISTRATION')
        officer.get_by_label('Reason / correction request').fill('Corrected evidence and deterministic evaluation independently inspected for synthetic registration.')
        officer.get_by_role('checkbox').check()
        officer.get_by_role('button', name='Record human decision').click()
        expect(officer.get_by_text('MANUALLY REVIEWED', exact=True)).to_be_visible(timeout=15000)
        officer.screenshot(path='.local/browser/deficient-corrected.png', full_page=True)
        other = browser.new_context(viewport={'width': 1440, 'height': 1000}).new_page()
        login(other, 'other-institution')
        expect(other.get_by_text(record['id'][:8].upper(), exact=False)).to_have_count(0)
        with portal_client('other-institution') as client:
            assert client.get('/deposits/' + record['id']).status_code == 404
        browser.close()


def test_browser_scanned_evidence_annotation_and_simulated_bank():
    from sentinel.synthetic import fixture_pdf
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        page = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(page, 'institution')
        page.get_by_role('button', name='+ Register deposit').click()
        page.get_by_label('Full reference').fill('SYN-OCR-' + uuid4().hex)
        page.get_by_label('Obligation / institution', exact=True).select_option('30000000-0000-0000-0000-000000000001')
        page.get_by_label('Declared amount (INR)').fill('3500000')
        page.get_by_label('Issue date', exact=True).fill('2016-10-01')
        page.get_by_label('Maturity date', exact=True).fill('2026-10-01')
        with page.expect_response(lambda r: r.url.endswith('/api/v1/deposits') and r.request.method == 'POST') as response:
            page.get_by_role('button', name='Save deposit').click()
        record = response.value.json()
        page.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        page.get_by_label('PDF file').set_input_files({'name': 'scanned-synthetic.pdf', 'mimeType': 'application/pdf',
                                                      'buffer': fixture_pdf('scanned')})
        page.get_by_role('button', name='Upload privately').click()
        expect(page.get_by_text('READY', exact=True)).to_be_visible(timeout=60000)
        preview = page.get_by_alt_text('Private PDF page preview; drag to select evidence')
        expect(preview).to_be_visible(timeout=15000)
        preview.scroll_into_view_if_needed()
        box = preview.bounding_box()
        assert box
        page.mouse.move(box['x'] + box['width'] * 0.08, box['y'] + box['height'] * 0.30)
        page.mouse.down()
        page.mouse.move(box['x'] + box['width'] * 0.90, box['y'] + box['height'] * 0.36, steps=5)
        page.mouse.up()
        page.get_by_label('Proposed typed value', exact=True).fill('350000000')
        page.get_by_label('Source transcription', exact=True).fill('Principal amount (INR): 35,00,000.00')
        page.get_by_label('Correction rationale', exact=True).fill('Original scanned region inspected; propose exact typed transcription.')
        page.get_by_role('button', name='Propose evidence correction', exact=True).click()
        expect(page.get_by_text('PROPOSED', exact=True)).to_be_visible()
        page.get_by_role('button', name='Run current evaluation').click()
        page.get_by_role('button', name='Submit for scrutiny').click()
        expect(page.get_by_text('PENDING SCRUTINY', exact=True)).to_be_visible()
        officer = browser.new_context(viewport={'width': 1440, 'height': 1100}).new_page()
        login(officer, 'reviewer')
        officer.get_by_text(record['id'][:8].upper(), exact=False).first.click()
        officer.get_by_label('Independent correction reason', exact=True).fill('Scanned original amount and bounded region independently inspected and confirmed.')
        officer.get_by_role('button', name='Record correction decision', exact=True).click()
        expect(officer.get_by_text('CONFIRMED', exact=True)).to_be_visible()
        officer.get_by_role('button', name='Run current evaluation').click()
        from test_sandbox_integrations import fixture_ledger
        ledger = fixture_ledger({**record, 'amount_paise': 400000000})
        officer.get_by_label('Independent bank ledger ID', exact=True).fill(ledger)
        officer.get_by_label('Sandbox transport behavior', exact=True).select_option('TRANSIENT_FAILURE')
        officer.get_by_role('button', name='Request independent bank check', exact=True).click()
        expect(officer.get_by_text('MISMATCH', exact=True)).to_be_visible(timeout=45000)
        expect(officer.get_by_text('INSTITUTION DECLARED', exact=True)).to_be_visible()
        officer.get_by_role('heading', name='Document intelligence & source review').scroll_into_view_if_needed()
        officer.screenshot(path='.local/browser/scanned-evidence.png', full_page=True)
        browser.close()


def test_browser_scoped_reports_and_csv_download():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        page = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True).new_page()
        login(page, 'reviewer')
        page.get_by_role('button', name='Reports').first.click()
        expect(page.get_by_role('heading', name='Scoped operations report')).to_be_visible()
        page.get_by_label('Search institution, bank, record ID or reference last four').fill('DEMO')
        page.get_by_role('button', name='Search scoped records', exact=True).click()
        with page.expect_download() as download:
            page.get_by_role('button', name='Export scoped CSV', exact=True).click()
        target = Path('.local/browser/scoped-report.csv')
        download.value.save_as(target)
        content = target.read_text(encoding='utf-8')
        assert 'SYNTHETIC' in content and 'reference_digest' not in content
        page.screenshot(path='.local/browser/reports.png', full_page=True)
        browser.close()


def test_browser_retries_lost_commit_response_without_duplicate_intake():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        page = browser.new_context(viewport={'width': 1440, 'height': 1000}).new_page()
        login(page, 'institution')
        keys, committed = {}, {}

        def lose_first_response(route):
            request = route.request
            if request.method != 'POST':
                route.continue_()
                return
            path = request.url.split('/api/v1')[-1]
            keys.setdefault(path, []).append(request.headers['idempotency-key'])
            response = route.fetch()  # Real API commits before the client sees a network loss.
            assert response.status == 200
            result = response.json()
            if path not in committed:
                committed[path] = result['id']
                route.abort('connectionreset')
            else:
                assert result['id'] == committed[path]
                route.fulfill(response=response)

        page.route('**/api/v1/deposits', lose_first_response)
        page.route('**/api/v1/deposits/*/documents', lose_first_response)
        page.get_by_role('button', name='+ Register deposit').click()
        page.get_by_label('Full reference').fill('SYN-RETRY-' + uuid4().hex)
        page.get_by_label('Obligation / institution', exact=True).select_option('30000000-0000-0000-0000-000000000001')
        page.get_by_label('Declared amount (INR)').fill('3500000')
        page.get_by_label('Issue date', exact=True).fill('2016-10-01')
        page.get_by_label('Maturity date', exact=True).fill('2026-10-01')
        page.get_by_role('button', name='Save deposit').click()
        expect(page.get_by_role('button', name='Save deposit')).not_to_be_visible(timeout=20000)
        record_id = committed['/deposits']
        page.get_by_text(record_id[:8].upper(), exact=False).first.click()
        page.get_by_label('PDF file').set_input_files({
            'name': 'retry.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_bytes()})
        page.get_by_role('button', name='Upload privately').click()
        expect(page.get_by_text('READY', exact=True)).to_be_visible(timeout=60000)
        assert len(keys) == 2
        assert all(len(attempts) == 2 and len(set(attempts)) == 1 for attempts in keys.values())
        assert len(page.get_by_text('READY', exact=True).all()) == 1
        page.screenshot(path='.local/browser/retried-intake.png', full_page=True)
        browser.close()
