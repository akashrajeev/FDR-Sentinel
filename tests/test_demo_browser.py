"""Qualify the static demo independently of the API, identity provider and workers."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

pytestmark = [pytest.mark.browser, pytest.mark.skipif(
    not os.getenv('DEMO_BASE_URL'), reason='Set DEMO_BASE_URL to a built static demo')]
BASE = os.getenv('DEMO_BASE_URL', 'http://127.0.0.1:4174').rstrip('/')
OUTPUT = Path('.local/demo-qa')


@pytest.fixture
def demo():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome')
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        errors, requests = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: requests.append(r.url) if '/api/' in r.url
                or ':8081/' in r.url else None)
        yield page, context, browser
        assert not errors, errors
        assert not requests, requests
        browser.close()


def enter(page):
    page.goto(BASE)
    page.get_by_role('button', name='Explore interactive demo').click()
    expect(page.get_by_label('Demo persona')).to_have_value('reviewer')
    expect(page.get_by_role('heading', name='Deposit operations', exact=True)).to_be_visible()
    page.screenshot(path=str(OUTPUT / 'overview.png'))


def scenario(page, name):
    page.get_by_label('Explore a scenario').select_option(label=name)


def persona(page, name):
    page.get_by_label('Demo persona').select_option(name)
    expect(page.get_by_label('Demo persona')).to_have_value(name)


def approval(page):
    page.get_by_label('Independent approver regulatory basis').fill(
        'I reviewed these synthetic examples and independent clearances. No financial authority.')
    page.get_by_role('checkbox').check()
    page.get_by_role('button', name='Attempt synthetic approval').click()


def clearance(page):
    page.get_by_label('PGRC reason').fill('Independent PGRC review of the bundled synthetic evidence.')
    page.get_by_role('button', name='Record PGRC decision').click()


def test_demo_pgrc_to_independent_issuance_and_persistence(demo):
    page, context, browser = demo
    enter(page)
    expect(page.get_by_role('button', name='Sign in securely')).to_have_count(0)
    scenario(page, 'PGRC blocks release')
    expect(page.get_by_role('heading', name='Release is blocked')).to_be_visible()
    approval(page)
    expect(page.get_by_role('alert').filter(has_text='Approval blocked: PGRC')).to_be_visible()
    page.screenshot(path=str(OUTPUT / 'pgrc-block.png'), full_page=True)
    page.get_by_role('button', name='Continue guided journey').click()
    clearance(page)
    page.get_by_role('button', name='Continue guided journey').click()
    approval(page)
    expect(page.locator('.case-steps .current')).to_contain_text('APPROVED SYNTHETIC')
    page.get_by_role('button', name='Continue guided journey').click()
    page.get_by_role('button', name='Issue synthetic NOC').click()
    expect(page.get_by_role('heading', name='Synthetic result issued')).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role('button', name='Download synthetic result').click()
    pdf = OUTPUT / 'synthetic-noc.pdf'
    download.value.save_as(pdf)
    import pymupdf
    with pymupdf.open(pdf) as document:
        assert 'NO OFFICIAL AUTHORITY' in document[0].get_text()
        document[0].get_pixmap().save(OUTPUT / 'synthetic-noc.png')
    page.reload()
    scenario(page, 'PGRC blocks release')
    expect(page.get_by_role('heading', name='Synthetic result issued')).to_be_visible()
    other = browser.new_context()
    visitor = other.new_page()
    visitor.goto(BASE + '/?demo=1')
    scenario(visitor, 'PGRC blocks release')
    expect(visitor.get_by_role('heading', name='Release is blocked')).to_be_visible()
    other.close()
    page.get_by_role('button', name='Reset demo', exact=True).click()
    page.get_by_role('button', name='Reset synthetic workspace').click()
    scenario(page, 'PGRC blocks release')
    expect(page.get_by_role('heading', name='Release is blocked')).to_be_visible()


def test_demo_submission_and_evidence_correction(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'New submission')
    page.get_by_role('button', name='Attach demo sample proof').click()
    page.get_by_role('button', name='Run current evaluation').click()
    page.get_by_role('button', name='Submit for scrutiny').click()
    persona(page, 'reviewer')
    page.get_by_label('Officer decision').select_option('ACCEPT_REGISTRATION')
    page.get_by_label('Reason / correction request').fill('Reviewed the bundled proof and current provisional sample checks.')
    page.get_by_label('I reviewed the original evidence').check()
    page.get_by_role('button', name='Record human decision').click()
    expect(page.get_by_text('MANUALLY REVIEWED', exact=True)).to_be_visible()
    scenario(page, 'Evidence mismatch')
    page.get_by_label('Reason / correction request').fill('Return because declared amount conflicts with sample evidence.')
    page.get_by_role('button', name='Record human decision').click()
    persona(page, 'institution')
    page.get_by_label('Amount (INR)', exact=True).fill('3500000')
    page.get_by_role('button', name='Save correction', exact=True).click()
    page.get_by_role('button', name='Run current evaluation').click()
    page.get_by_role('button', name='Submit for scrutiny').click()
    persona(page, 'reviewer')
    page.get_by_label('Discrepancy resolution reason').fill('Declaration corrected to match the original sample document and reevaluated.')
    page.get_by_role('button', name='Resolve corrected discrepancy').click()
    page.get_by_label('Officer decision').select_option('ACCEPT_REGISTRATION')
    page.get_by_label('Reason / correction request').fill('Independent sample scrutiny complete after corrected discrepancy disposition.')
    page.get_by_label('I reviewed the original evidence').check()
    page.get_by_role('button', name='Record human decision').click()
    expect(page.get_by_text('MANUALLY REVIEWED', exact=True)).to_be_visible()
    page.screenshot(path=str(OUTPUT / 'corrected-record.png'), full_page=True)


def test_demo_hold_rtgs_renewal_reports_import_and_operator(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Active legal hold')
    persona(page, 'pgrc')
    clearance(page)
    persona(page, 'approver')
    approval(page)
    expect(page.get_by_role('alert').filter(has_text='Active hold')).to_be_visible()
    page.get_by_label('Resolution and authority').fill('Independent disposition supported by the bundled synthetic legal evidence.')
    page.get_by_role('button', name='Resolve with evidence').click()
    approval(page)
    expect(page.locator('.case-steps .current')).to_contain_text('APPROVED SYNTHETIC')
    scenario(page, 'RTGS sanction branch')
    persona(page, 'pgrc')
    clearance(page)
    persona(page, 'approver')
    approval(page)
    persona(page, 'issuer')
    page.get_by_role('button', name='Issue synthetic sanction order').click()
    expect(page.get_by_role('heading', name='Synthetic result issued')).to_be_visible()
    scenario(page, 'Renewal and maturity')
    page.get_by_label('Officer policy basis').fill('Independent review confirms later covering synthetic replacement evidence.')
    page.get_by_role('button', name='Authorize replacement').click()
    expect(page.get_by_text('APPROVED', exact=True)).to_be_visible()
    page.get_by_role('button', name='Run maturity monitor').click()
    expect(page.get_by_text('Email: SIMULATED_NOT_SENT', exact=False).first).to_be_visible()
    scenario(page, 'Reports and escalation')
    expect(page.get_by_role('heading', name='Interventions and escalation')).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role('button', name='Export scoped CSV').click()
    download.value.save_as(OUTPUT / 'deposits.csv')
    assert 'BROWSER_SIMULATION' in (OUTPUT / 'deposits.csv').read_text()
    scenario(page, 'Legacy import')
    page.get_by_role('button', name='Preview bundled legacy sample').click()
    page.get_by_role('button', name='Commit validated DRAFT records').click()
    expect(page.get_by_role('status').filter(has_text='1 DRAFT')).to_be_visible()
    scenario(page, 'Scoped assignments')
    expect(page.get_by_role('heading', name='Technical operator workspace')).to_be_visible()
    expect(page.get_by_label('Officer principal')).to_be_visible()


def test_demo_mobile_dark_storage_failure_and_personas(demo):
    page, context, _ = demo
    context.add_init_script("const get = Storage.prototype.getItem; Storage.prototype.getItem = function(k) { if(k === 'sentinel-interactive-demo-v1') throw Error('denied'); return get.call(this,k); }; const set = Storage.prototype.setItem; Storage.prototype.setItem = function(k,v) { if(k === 'sentinel-interactive-demo-v1') throw Error('denied'); return set.call(this,k,v); };")
    page.set_viewport_size({'width': 390, 'height': 844})
    page.emulate_media(color_scheme='dark')
    enter(page)
    expect(page.get_by_role('status').filter(has_text='Browser storage is unavailable')).to_be_visible()
    for name in ['institution', 'pgrc', 'vigilance', 'grants', 'approver', 'issuer', 'auditor', 'operator', 'reviewer']:
        persona(page, name)
    for tab in ['Overview', 'Deposits', 'Institutions', 'Release cases', 'Reports', 'Audit trail']:
        page.get_by_role('button', name=tab, exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(OUTPUT / 'mobile-dark.png'), full_page=True)
    page.get_by_role('button', name='Exit demo').click()
    expect(page.get_by_role('button', name='Explore interactive demo')).to_be_visible()


def test_demo_ocr_correction_recovery_revalidation_and_file_intake(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'OCR and advisory AI')
    page.get_by_role('button', name='Prepare a human correction proposal').click()
    page.get_by_label('Correction rationale').fill('Confirm the amount against the linked bundled sample region.')
    page.get_by_role('button', name='Propose evidence correction').click()
    expect(page.get_by_text('PROPOSED', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Record correction decision')).to_have_count(0)
    persona(page, 'reviewer')
    page.get_by_label('Independent correction reason').fill('Independently inspected the sample amount and source quotation.')
    page.get_by_role('button', name='Record correction decision').click()
    expect(page.get_by_text('CONFIRMED', exact=True)).to_be_visible()
    page.get_by_role('button', name='Run current evaluation').click()
    scenario(page, 'Worker and source recovery')
    page.get_by_role('button', name='Retry failed document processing').click()
    expect(page.get_by_text('READY', exact=True).first).to_be_visible(timeout=15000)
    page.get_by_role('button', name='Retry sandbox exchange').click()
    expect(page.get_by_text('SIMULATED_BANK_CHECK · SUCCEEDED', exact=True)).to_be_visible(timeout=15000)
    page.get_by_label('Independent bank ledger ID').fill('SB-0009')
    page.get_by_label('Sandbox transport behavior').select_option('DELAYED')
    page.get_by_role('button', name='Request independent bank check').click()
    expect(page.get_by_text('SIMULATED_PENDING', exact=True)).to_be_visible()
    expect(page.get_by_text('SIMULATED_PENDING', exact=True)).to_have_count(0, timeout=15000)
    scenario(page, 'Policy revalidation')
    page.get_by_role('button', name='Request fresh policy scrutiny').click()
    expect(page.get_by_role('button', name='Run current evaluation')).to_be_visible()
    expect(page.get_by_role('heading', name='Officer decisions')).to_be_visible()
    scenario(page, 'New submission')
    page.get_by_text('Explore upload, scanning, OCR and processing failures', exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('button', name='Download sample upload PDF').click()
    sample = OUTPUT / 'synthetic-intake.pdf'
    download.value.save_as(sample)
    page.get_by_label('Synthetic PDF file (local only)').set_input_files(sample)
    page.get_by_role('button', name='Try local PDF intake').click()
    expect(page.get_by_text('READY', exact=True).first).to_be_visible(timeout=15000)
    page.get_by_label('Sample processing outcome').select_option('MALWARE')
    page.get_by_role('button', name='Attach selected processing example').click()
    expect(page.get_by_text('REJECTED', exact=True).first).to_be_visible()
    expect(page.get_by_role('button', name='Run current evaluation')).to_be_disabled()


def test_demo_csv_file_atomicity_and_unknown_policy(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Legacy import')
    with page.expect_download() as download:
        page.get_by_role('button', name='Download synthetic CSV example').click()
    sample = OUTPUT / 'synthetic-import.csv'
    download.value.save_as(sample)
    original = sample.read_bytes()
    invalid = original + original.split(b'\n')[1].replace(b'0088', b'0089').replace(b'350000000', b'-1') + b'\n'
    page.get_by_label('Legacy CSV file').set_input_files({'name': 'invalid.csv', 'mimeType': 'text/csv', 'buffer': invalid})
    page.get_by_role('button', name='Validate import preview').click()
    expect(page.get_by_role('alert')).to_contain_text('positive supported amount')
    page.get_by_label('Legacy CSV file').set_input_files(sample)
    page.get_by_role('button', name='Validate import preview').click()
    page.get_by_role('button', name='Commit validated DRAFT records').click()
    expect(page.get_by_role('status').filter(has_text='1 DRAFT')).to_be_visible()
    page.get_by_role('button', name='Validate import preview').click()
    expect(page.get_by_role('alert')).to_contain_text('already exists')
    scenario(page, 'Unknown regulatory context')
    expect(page.get_by_text('REQUIRES HUMAN REVIEW', exact=True).first).to_be_visible()


def test_demo_operator_grants_policy_and_escalation(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Scoped assignments')
    page.get_by_label('Officer principal').select_option('demo-auditor')
    page.get_by_label('Assigned role').select_option('REVIEWER')
    page.get_by_label('Assignment reason').fill('Synthetic temporary assignment for an independently scoped reviewer.')
    page.get_by_role('button', name='Assign scoped officer').click()
    expect(page.get_by_role('button', name='Disable', exact=True)).to_be_visible()
    persona(page, 'auditor')
    page.get_by_role('button', name='Deposits', exact=True).click()
    page.get_by_role('button', name='FDR00002', exact=True).click()
    expect(page.get_by_label('Officer decision')).to_be_visible()
    scenario(page, 'Scoped assignments')
    page.once('dialog', lambda dialog: dialog.accept('Revoke this temporary synthetic assignment after the demonstration.'))
    page.get_by_role('button', name='Disable', exact=True).click()
    expect(page.get_by_role('button', name='Enable', exact=True)).to_be_visible()
    persona(page, 'auditor')
    page.get_by_role('button', name='Deposits', exact=True).click()
    page.get_by_role('button', name='FDR00002', exact=True).click()
    expect(page.get_by_label('Officer decision')).to_have_count(0)
    scenario(page, 'Reports and escalation')
    page.get_by_text('Configure follow-up deadlines and supervisor', exact=True).click()
    page.get_by_label('review hours', exact=True).fill('72')
    page.get_by_label('Operations policy reason').fill('Configure synthetic product service levels for the judge exercise.')
    page.get_by_role('button', name='Save operations policy').click()
    expect(page.get_by_role('status').filter(has_text='Operations policy saved')).to_be_visible()
    page.get_by_label('Synthetic operations clock (optional)').fill('2026-11-01T12:00')
    page.get_by_role('button', name='Run intervention scan').click()
    page.get_by_role('button', name='Simulated notification inbox').click()
    expect(page.get_by_role('region', name='Simulated notification inbox').get_by_text('SIMULATED ESCALATION', exact=True).first).to_be_visible()


def test_demo_new_case_return_and_rejected_clearance(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Renewal and maturity')
    persona(page, 'institution')
    page.get_by_label('Accepted deposit', exact=True).select_option('rpgf0012-demo')
    page.get_by_role('button', name='Create release case').click()
    page.get_by_role('button', name='Attach demo release evidence').click()
    page.get_by_role('button', name='Submit to bureaus').click()
    persona(page, 'reviewer')
    page.get_by_label('Return for correction reason').fill('Synthetic return to demonstrate retained clearance history and correction.')
    page.get_by_role('button', name='Return release case').click()
    persona(page, 'institution')
    page.get_by_role('button', name='Submit to bureaus').click()
    persona(page, 'grants')
    page.get_by_label('GRANTS disposition').select_option('REJECTED')
    page.get_by_label('GRANTS reason').fill('Synthetic rejection: further independent evidence is required.')
    page.get_by_role('button', name='Record GRANTS decision').click()
    persona(page, 'approver')
    approval(page)
    expect(page.get_by_role('alert')).to_contain_text('GRANTS clearance pending or rejected')
    persona(page, 'reviewer')
    page.get_by_label('Return for correction reason').fill('Synthetic return after rejection to collect fresh independent clearances.')
    page.get_by_role('button', name='Return release case').click()
    persona(page, 'institution')
    page.get_by_role('button', name='Submit to bureaus').click()
    for role in ['pgrc', 'vigilance', 'grants']:
        persona(page, role)
        bureau = role.upper()
        page.get_by_label(f'{bureau} disposition').select_option('CLEARED')
        page.get_by_label(f'{bureau} reason').fill('Fresh independent synthetic disposition supported by sample evidence.')
        page.get_by_role('button', name=f'Record {bureau} decision').click()
    persona(page, 'approver')
    approval(page)
    persona(page, 'issuer')
    page.get_by_role('button', name='Issue synthetic NOC').click()
    with page.expect_download() as download:
        page.get_by_role('button', name='Download synthetic result').click()
    target = OUTPUT / 'synthetic-rpgf-noc.pdf'
    download.value.save_as(target)
    import pymupdf
    with pymupdf.open(target) as document:
        assert 'SAMPLE NOC' in document[0].get_text()
        assert 'SAMPLE SANCTION' not in document[0].get_text()


def test_demo_onboarding_all_instrument_types_and_registry_unknown(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Institution onboarding')
    page.get_by_role('button', name='+ Onboard institution').click()
    page.get_by_label('Legal name', exact=True).fill('Synthetic Judging Academy')
    page.get_by_label('Institution identifier (synthetic)').fill('SYN-JUDGE-ACADEMY')
    page.get_by_label('Exceptional history / uncertainty').select_option('no')
    page.get_by_role('button', name='Create institution & obligation').click()
    card = page.locator('.institution-grid > section').filter(has_text='Synthetic Judging Academy')
    card.get_by_role('button', name='Check sandbox institution registry').click()
    expect(card.get_by_text('SIMULATED NOT FOUND', exact=True)).to_be_visible()
    for index, kind in enumerate(['FDR', 'RPGF', 'RTGS', 'ONLINE', 'OTHER_LEGACY']):
        page.get_by_role('button', name='+ Register deposit').click()
        obligation = page.get_by_label('Obligation / institution', exact=True)
        value = obligation.locator('option').filter(has_text='Synthetic Judging Academy').get_attribute('value')
        obligation.select_option(value)
        page.get_by_label('Deposit type', exact=True).select_option(kind)
        page.get_by_label('Full reference').fill(f'SYN-JUDGE-{2100 + index}')
        page.get_by_label('Declared amount (INR)').fill('3500000')
        if kind == 'FDR':
            page.get_by_label('Issue date', exact=True).fill('2016-10-01')
            page.get_by_label('Maturity date', exact=True).fill('2026-10-01')
        else:
            page.get_by_label('Deposited on', exact=True).fill('2016-10-01')
        page.get_by_role('button', name='Save deposit', exact=True).click()
        expect(page.get_by_role('heading', name='Document evidence')).to_be_visible()
        page.get_by_role('button', name='All deposits', exact=False).click()
    page.get_by_label('Search deposit records', exact=True).fill('Synthetic Judging Academy')
    page.get_by_role('button', name='Search register', exact=True).click()
    expect(page.locator('.register-panel tbody tr')).to_have_count(5)


def test_demo_pagination_and_complete_export(demo):
    page, _, _ = demo
    enter(page)
    scenario(page, 'Legacy import')
    header = 'obligation_id,deposit_type,bank_code,reference,amount_paise,issue_date,maturity_date,deposited_on\n'
    rows = ''.join(f'oblg0001-demo,FDR,SYN-BULK,SYN-BULK-{3000+i},350000000,2016-10-01,2026-10-01,\n' for i in range(60))
    page.get_by_label('Legacy CSV file').set_input_files({'name': 'synthetic-bulk.csv', 'mimeType': 'text/csv', 'buffer': (header + rows).encode()})
    page.get_by_role('button', name='Validate import preview').click()
    page.get_by_role('button', name='Commit validated DRAFT records').click()
    expect(page.get_by_role('status').filter(has_text='60 DRAFT')).to_be_visible()
    page.get_by_role('button', name='Deposits', exact=True).click()
    page.get_by_label('Search deposit records', exact=True).fill('SYN-BULK')
    page.get_by_role('button', name='Search register', exact=True).click()
    expect(page.locator('.register-panel tbody tr')).to_have_count(50)
    page.get_by_role('button', name='Next records', exact=False).click()
    expect(page.locator('.register-panel tbody tr')).to_have_count(10)
    scenario(page, 'Reports and escalation')
    with page.expect_download() as download:
        page.get_by_role('button', name='Export scoped CSV').click()
    target = OUTPUT / 'full-scope-export.csv'
    download.value.save_as(target)
    import csv
    with target.open(newline='') as stream:
        assert len(list(csv.DictReader(stream))) == 74
