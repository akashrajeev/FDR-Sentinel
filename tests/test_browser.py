import os
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
    page.get_by_label('Password', exact=True).fill(os.environ[f'DEMO_{username.upper()}_PASSWORD'])
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
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.getenv('BROWSER_CHANNEL', 'chromium'))
        def desk(username):
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            page = context.new_page()
            login(page, username)
            page.get_by_role('button', name='Release cases').first.click()
            return page
        maker = desk('institution')
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
        issuer.screenshot(path='.local/browser/synthetic-issued.png', full_page=True)
        browser.close()
