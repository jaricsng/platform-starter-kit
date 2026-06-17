"""Minimal service — proves the platform-starter-kit pieces work end-to-end.

A single FastAPI app with /health and /ready routes, instrumented with
OpenTelemetry so traces land in Jaeger and metrics are scraped by Prometheus
when run with the observability overlay (../../observability).

Run: docker compose up   (see README.md in this directory)
"""
import logging

from fastapi import FastAPI
from opentelemetry import trace

from telemetry import setup_telemetry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("minimal-service")

app = FastAPI(title="Minimal Service")
setup_telemetry(app)

tracer = trace.get_tracer(__name__)


@app.get("/health")
def health():
    with tracer.start_as_current_span("health-check"):
        logger.info("health check ok")
        return {"status": "ok"}


@app.get("/ready")
def ready():
    with tracer.start_as_current_span("readiness-check"):
        return {"status": "ready"}


@app.get("/")
def root():
    return {"service": "minimal-service", "see": "/health, /ready, /metrics"}
