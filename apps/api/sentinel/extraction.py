"""Bounded digital extraction and real Tesseract OCR after successful malware scan."""
import csv
import io
import re
import subprocess
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pymupdf

from sentinel.config import settings

ALGORITHM = 'typed-digital-tesseract-v2'
DATE_TOKEN = r'(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})'
PATTERNS = {
    'amount_paise': [
        (re.compile(r'Amount\s+paise\s*[:\-]?\s*(\d+)(?![\d.,])', re.I), 'PAISE'),
        (re.compile(r'(?:Principal\s+(?:amount|sum)|Deposit\s+amount|Amount\s+deposited)'
                    r'\s*(?:\(?INR\)?|Rs\.?|₹)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)(?![\d.,])', re.I), 'RUPEES'),
    ],
    'issue_date': [(re.compile(r'(?:Issue\s+date|Date\s+of\s+issue|Issued\s+on)\s*[:\-]?\s*' + DATE_TOKEN, re.I), 'DATE')],
    'maturity_date': [(re.compile(r'(?:Maturity\s+date|Date\s+of\s+maturity|Matures\s+on)\s*[:\-]?\s*' + DATE_TOKEN, re.I), 'DATE')],
    'institution_external_id': [(re.compile(r'Institution\s+(?:ID|identifier)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9-]{4,63})', re.I), 'TEXT')],
}


def normalize_value(value: str, kind: str):
    if kind == 'DATE':
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d %b %Y'):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError('Unrecognized date')
    if kind in ('PAISE', 'RUPEES'):
        number = Decimal(value.replace(',', '')) * (100 if kind == 'RUPEES' else 1)
        if number != number.to_integral_value() or not 0 < number <= 1_000_000_000_000:
            raise ValueError('Unsupported amount')
        return int(number)
    return value


def parse_fields(text: str, page: int, method: str, locate, confidence=None):
    evidence = []
    for field, patterns in PATTERNS.items():
        for pattern, kind in patterns:
            for match in pattern.finditer(text):
                try:
                    value = normalize_value(match[1], kind)
                except (ValueError, InvalidOperation):
                    continue
                evidence.append({'field': field, 'value': value, 'page': page,
                                 'offset': match.start(1), 'bounds': locate(match.group(0)),
                                 'quote': match.group(0)[:240], 'method': method,
                                 'algorithm': ALGORITHM, 'confidence': confidence})
    return evidence


def ocr_page(page):
    if page.rect.width * page.rect.height * (180 / 72) ** 2 > 20_000_000:
        raise ValueError('Raster page pixel limit exceeded')
    pixmap = page.get_pixmap(dpi=180, alpha=False)
    if pixmap.width * pixmap.height > 20_000_000:
        raise ValueError('Raster page pixel limit exceeded')
    try:
        process = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', 'eng', '--psm', '6', 'tsv'],
                                 input=pixmap.tobytes('png'), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=35, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Tesseract OCR unavailable') from exc
    lines = {}
    for row in csv.DictReader(io.StringIO(process.stdout.decode('utf-8')), delimiter='\t'):
        if row.get('text', '').strip() and row.get('level') == '5':
            key = (row['block_num'], row['par_num'], row['line_num'])
            lines.setdefault(key, []).append(row)
    blocks = []
    for words in lines.values():
        line = ' '.join(w['text'] for w in words)
        x0, y0 = min(int(w['left']) for w in words), min(int(w['top']) for w in words)
        x1 = max(int(w['left']) + int(w['width']) for w in words)
        y1 = max(int(w['top']) + int(w['height']) for w in words)
        scale = 72 / 180
        blocks.append({'text': line, 'bounds': [x0 * scale, y0 * scale, x1 * scale, y1 * scale],
                       'confidence': sum(max(0, float(w['conf'])) for w in words) / (100 * len(words))})
    return blocks


def extract_document(data: bytes, use_ai: bool | None = None):
    if not data.startswith(b'%PDF-'):
        raise ValueError('Invalid PDF signature')
    evidence, source_pages, page_sizes = [], [], []
    ocr_pages = 0
    try:
        pdf = pymupdf.open(stream=data, filetype='pdf')
    except Exception as exc:
        raise ValueError('Malformed PDF') from exc
    with pdf:
        if pdf.needs_pass or not 1 <= len(pdf) <= settings().max_pdf_pages:
            raise ValueError('Encrypted/empty PDF or page limit exceeded')
        for index, page in enumerate(pdf):
            if page.rect.width > 3000 or page.rect.height > 3000:
                raise ValueError('PDF dimensions exceed processing limit')
            page_sizes.append([page.rect.width, page.rect.height])
            text = page.get_text()[:50000]
            if len(text.strip()) >= 20:
                def locate(quote):
                    boxes = page.search_for(quote)
                    return list(boxes[0]) if boxes else None
                evidence.extend(parse_fields(text, index + 1, 'DIGITAL_PDF', locate))
            else:
                blocks = ocr_page(page)
                text = '\n'.join(b['text'] for b in blocks)
                ocr_pages += 1
                for block in blocks:
                    evidence.extend(parse_fields(block['text'], index + 1, 'TESSERACT_OCR',
                                                 lambda _, b=block: b['bounds'], block['confidence']))
            source_pages.append({'page': index + 1, 'text': text[:12000]})
    metadata = {'algorithm': ALGORITHM, 'page_count': len(page_sizes), 'page_sizes': page_sizes,
                'ocr_pages': ocr_pages, 'ai_status': 'DISABLED', 'ai_proposals': []}
    ai_enabled = use_ai if use_ai is not None else settings().ai_assist_enabled
    if ai_enabled:
        from sentinel.local_ai import propose_fields
        try:
            metadata['ai_proposals'], rejected = propose_fields(source_pages[:3])
            metadata['ai_status'] = 'COMPLETED_ASSISTIVE_ONLY'
            metadata['ai_rejected_proposals'] = rejected
        except Exception:
            metadata['ai_status'] = 'UNAVAILABLE_NO_AUTHORITY'
    return evidence, metadata


def render_previews(data: bytes):
    with pymupdf.open(stream=data, filetype='pdf') as pdf:
        return {index + 1: pdf[index].get_pixmap(dpi=90, alpha=False).tobytes('png')
                for index in range(min(3, len(pdf)))}
