"""Payload-free OTel traces; local JSON export by default, optional configured OTLP."""
import functools
import json
import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger('sentinel.traces')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.propagate = False
propagator = TraceContextTextMapPropagator()


class SafeJsonExporter(SpanExporter):
    def export(self, spans):
        for span in spans:
            logger.info(json.dumps({'kind': 'otel_span', 'name': span.name,
                'trace_id': f'{span.context.trace_id:032x}', 'span_id': f'{span.context.span_id:016x}',
                'parent_span_id': f'{span.parent.span_id:016x}' if span.parent else None,
                'service': span.resource.attributes.get('service.name'),
                'status': span.status.status_code.name,
                'duration_ms': round((span.end_time - span.start_time) / 1e6, 3),
                'attributes': dict(span.attributes or {})}))
        return SpanExportResult.SUCCESS


def configure(service):
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    provider = TracerProvider(resource=Resource.create({'service.name': service}))
    provider.add_span_processor(SimpleSpanProcessor(SafeJsonExporter()))
    endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT')
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint.rstrip('/') + '/v1/traces')))
    trace.set_tracer_provider(provider)


def capture_context():
    carrier = {}
    propagator.inject(carrier)
    return carrier


def traced(name):
    def decorate(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            carrier = getattr(getattr(args[0], 'request', None), 'headers', None) if args else None
            context = propagator.extract(carrier) if carrier else None
            with trace.get_tracer('sentinel').start_as_current_span(name, context=context,
                    record_exception=False, set_status_on_exception=False) as span:
                try:
                    result = function(*args, **kwargs)
                    if result == 'DEAD_LETTER':
                        span.set_status(Status(StatusCode.ERROR))
                    return result
                except Exception as exc:
                    span.set_attribute('error.type', type(exc).__name__)
                    span.set_status(Status(StatusCode.ERROR))
                    raise
        return wrapper
    return decorate
