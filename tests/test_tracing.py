import re
from uuid import uuid4

import pytest
from conftest import create_deposit, pdf_bytes
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select

pytestmark = pytest.mark.integration


def test_trace_context_survives_transactional_outbox(clients):
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    maker = clients()
    deposit = create_deposit(maker)
    response = maker.post(f"/api/v1/deposits/{deposit['id']}/documents", files={
        'file': ('trace.pdf', pdf_bytes(), 'application/pdf')}, headers={'Idempotency-Key': str(uuid4())})
    assert response.status_code == 200
    trace_id = response.headers['x-trace-id']
    assert re.fullmatch('[a-f0-9]{32}', trace_id) and int(trace_id, 16) != 0
    with session_factory()() as db:
        event = db.scalar(select(Outbox).where(Outbox.aggregate_id == response.json()['id']))
        event_id, carrier = event.id, event.trace_context
    assert trace_id in carrier['traceparent']
    assert process_document.apply(args=[event_id], headers=carrier).get() == 'READY'
    spans = [s for s in exporter.get_finished_spans() if f'{s.context.trace_id:032x}' == trace_id]
    assert any(s.name == 'document.process' and s.parent for s in spans)
    assert all('authorization' not in str(s.attributes).lower() for s in spans)
    private_query = 'SYN-PRIVATE-REFERENCE-DO-NOT-TRACE'
    maker.get('/api/v1/search/deposits', params={'q': private_query})
    assert private_query not in str([s.attributes for s in exporter.get_finished_spans()])
