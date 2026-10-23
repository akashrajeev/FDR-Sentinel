import re

import pymupdf

from sentinel.config import settings

PATTERNS = {
    'amount_paise': re.compile(r'Amount\s+paise\s*:\s*(\d+)', re.I),
    'issue_date': re.compile(r'Issue\s+date\s*:\s*(\d{4}-\d{2}-\d{2})', re.I),
    'maturity_date': re.compile(r'Maturity\s+date\s*:\s*(\d{4}-\d{2}-\d{2})', re.I),
}


def validate_and_extract(data: bytes) -> list:
    """Called ONLY after malware scan. Never parse quarantined bytes in the API."""
    if not data.startswith(b'%PDF-'):
        raise ValueError('Invalid PDF signature')
    evidence = []
    with pymupdf.open(stream=data, filetype='pdf') as pdf:
        if pdf.needs_pass or not 1 <= len(pdf) <= settings().max_pdf_pages:
            raise ValueError('Encrypted/empty PDF or page limit exceeded')
        for index, page in enumerate(pdf):
            text = page.get_text()
            for field, pattern in PATTERNS.items():
                for match in pattern.finditer(text):
                    boxes = page.search_for(match.group(0))
                    evidence.append({'field': field,
                                     'value': int(match[1]) if field == 'amount_paise' else match[1],
                                     'page': index + 1, 'offset': match.start(1),
                                     'bounds': list(boxes[0]) if boxes else None,
                                     'method': 'DIGITAL_PDF_REGEX', 'algorithm': 'synthetic-label-parser-v1',
                                     'confidence': None})
    return evidence
