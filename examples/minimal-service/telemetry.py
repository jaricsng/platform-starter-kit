"""OpenTelemetry setup — wires traces to Jaeger and metrics to Prometheus.

Minimal version of the pattern in platform-starter-kit/dotnet/ServiceDefaults
(the .NET equivalent) for a plain Python/FastAPI service with no database.
Call setup_telemetry(app) once at application startup.
"""
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from prometheus_client import make_asgi_app


def setup_telemetry(app) -> None:
    """Configure OTel SDK, auto-instrument FastAPI, mount /metrics.

    Reads OTLP_ENDPOINT (default http://jaeger:4317), OTEL_ENABLED
    (default "true"), and OTEL_SERVICE_NAME (default "app", matching
    observability/prometheus.yml's default job name) from the environment
    — set OTEL_ENABLED=false to skip wiring entirely (e.g. in unit tests).
    """
    if os.environ.get("OTEL_ENABLED", "true").lower() == "false":
        return

    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://jaeger:4317")

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "app"),
            ResourceAttributes.SERVICE_VERSION: "0.1.0",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: "development",
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)

    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )

    app.mount("/metrics", make_asgi_app())
