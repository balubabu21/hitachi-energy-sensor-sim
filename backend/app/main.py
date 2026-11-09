"""FastAPI application exposing the product/sensor catalogue and mock data."""
from __future__ import annotations

import inspect
import json
import logging
import os
import pprint
import shlex
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Any

from azure.communication.email import EmailClient
from azure.core.exceptions import AzureError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import catalog
from .generator import generate_readings
from .models import FieldSpec, Product, SensorFieldSchema, SensorSpec, SensorSubmission

app = FastAPI(
    title="Hitachi Energy Sensor Simulator API",
    version="1.0.0",
    description="Mock sensor data for Hitachi Energy product families (simulation only).",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

GENERATOR_SOURCE = (Path(__file__).parent / "generator.py").read_text(encoding="utf-8")
GENERATOR_KEYS = ("name", "dtype", "min", "max", "nominal", "precision", "options", "p_true", "labels", "step")
SENSOR_REQUEST_RECIPIENT = "balu.babu@method.com"
SENSOR_REQUEST_WINDOW_S = 3600
SENSOR_REQUEST_LIMIT = 3
_sensor_request_times: dict[str, deque[float]] = defaultdict(deque)
_sensor_request_lock = Lock()
logger = logging.getLogger(__name__)


def _field_out(f: FieldSpec) -> dict[str, Any]:
    d = f.model_dump(exclude_none=True)
    d["json_type"] = f.json_type
    return d


def _generator_spec(f: FieldSpec) -> dict[str, Any]:
    d = f.model_dump(exclude_none=True)
    return {k: d[k] for k in GENERATOR_KEYS if k in d}


def _lookup(product_id: str, sensor_id: str):
    product, sensor = catalog.get_sensor(product_id, sensor_id)
    if not product:
        raise HTTPException(404, f"Unknown product '{product_id}'")
    if not sensor:
        raise HTTPException(404, f"Unknown sensor '{sensor_id}' for product '{product_id}'")
    return product, sensor


def _asset_id(product_id: str) -> str:
    initials = "".join(w[0] for w in product_id.split("-")).upper()
    return f"HE-{initials}-0001"


def _check_sensor_request_rate(submitter_email: str) -> None:
    now = time.monotonic()
    cutoff = now - SENSOR_REQUEST_WINDOW_S
    with _sensor_request_lock:
        for email, timestamps in list(_sensor_request_times.items()):
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                del _sensor_request_times[email]

        recent_requests = _sensor_request_times[submitter_email.lower()]
        if len(recent_requests) >= SENSOR_REQUEST_LIMIT:
            raise HTTPException(
                429,
                "Only three sensor requests per submitter email are allowed each hour.",
            )
        recent_requests.append(now)


def _mock_response(
    product: Product,
    sensor: SensorSpec,
    fields: list[FieldSpec],
    count: int,
    interval_s: int | None,
    seed: int | None,
    anomaly_rate: float,
    asset_id: str | None,
) -> dict[str, Any]:
    interval = interval_s or sensor.sample_interval_s
    readings = generate_readings(
        sensor.id,
        [_generator_spec(field) for field in fields],
        asset_id=asset_id or _asset_id(product.id),
        count=count,
        interval_s=interval,
        seed=seed,
        anomaly_rate=anomaly_rate,
    )
    return {
        "product_id": product.id,
        "sensor_id": sensor.id,
        "protocol": sensor.protocol,
        "interval_s": interval,
        "count": count,
        "seed": seed,
        "readings": readings,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sensor-requests")
def submit_sensor_request(submission: SensorSubmission) -> dict[str, str]:
    product = catalog.get_product(submission.product_id)
    if not product:
        raise HTTPException(404, f"Unknown product '{submission.product_id}'")
    if product.name != submission.product_name:
        raise HTTPException(422, "Product name does not match the selected product")

    connection_string = os.getenv("ACS_EMAIL_CONNECTION_STRING")
    sender_address = os.getenv("ACS_EMAIL_SENDER_ADDRESS")
    if not connection_string or not sender_address:
        raise HTTPException(
            503,
            "Sensor request email is not configured. Configure Azure Communication Services Email first.",
        )

    _check_sensor_request_rate(submission.submitter_email)
    sensor = submission.sensor
    fields = [field.model_dump(exclude_none=True) for field in sensor.fields]
    body = (
        "A browser-created sensor was submitted for permanent-addition review.\n\n"
        f"Product: {submission.product_name} ({submission.product_id})\n"
        f"Sensor ID: {sensor.id}\n"
        f"Name: {sensor.name}\n"
        f"Description: {sensor.description}\n"
        f"Measurement principle: {sensor.principle}\n"
        f"Protocol: {sensor.protocol}\n"
        f"Sample interval: {sensor.sample_interval_s} seconds\n\n"
        f"Submitter: {submission.submitter_name}\n"
        f"Submitter email: {submission.submitter_email}\n"
        f"Hitachi Energy approver: {submission.approver_email}\n\n"
        f"Fields:\n{json.dumps(fields, indent=2, ensure_ascii=False)}\n"
    )
    message = {
        "senderAddress": sender_address,
        "recipients": {"to": [{"address": SENSOR_REQUEST_RECIPIENT}]},
        "content": {
            "subject": f"Sensor addition request: {sensor.id}",
            "plainText": body,
        },
    }

    client = None
    try:
        client = EmailClient.from_connection_string(connection_string)
        result = client.begin_send(message).result(timeout=60)
    except (AzureError, TimeoutError, ValueError) as exc:
        logger.exception("Azure Communication Services failed to send a sensor review request")
        raise HTTPException(502, "Azure Communication Services could not send the review request.") from exc
    finally:
        if client is not None:
            client.close()

    result_status = result.get("status")
    if str(result_status).lower() != "succeeded":
        logger.error("Azure Communication Services returned email status %r", result_status)
        raise HTTPException(502, "Azure Communication Services did not confirm delivery of the review request.")

    return {"status": "sent"}


@app.get("/api/products")
def list_products() -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "group": p.group,
            "description": p.description,
            "url": p.url,
            "sensor_count": len(p.sensors),
            "sensors": [{"id": s.id, "name": s.name} for s in p.sensors],
        }
        for p in catalog.PRODUCTS
    ]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    p = catalog.get_product(product_id)
    if not p:
        raise HTTPException(404, f"Unknown product '{product_id}'")
    data = p.model_dump(exclude={"sensors"})
    data["sensors"] = [
        {**s.model_dump(exclude={"fields"}), "fields": [_field_out(f) for f in s.fields]} for s in p.sensors
    ]
    data["envelope_fields"] = catalog.ENVELOPE_FIELDS
    return data


@app.get("/api/products/{product_id}/sensors/{sensor_id}/mock")
def mock_data(
    product_id: str,
    sensor_id: str,
    count: int = Query(10, ge=1, le=1000),
    interval_s: int | None = Query(None, ge=1, le=86400),
    seed: int | None = Query(None),
    anomaly_rate: float = Query(0.0, ge=0.0, le=1.0),
    asset_id: str | None = Query(None, max_length=64),
) -> dict[str, Any]:
    product, sensor = _lookup(product_id, sensor_id)
    return _mock_response(
        product, sensor, sensor.fields, count, interval_s, seed, anomaly_rate, asset_id
    )


@app.post("/api/products/{product_id}/sensors/{sensor_id}/mock")
def mock_custom_data(
    product_id: str,
    sensor_id: str,
    schema: SensorFieldSchema,
    count: int = Query(10, ge=1, le=1000),
    interval_s: int | None = Query(None, ge=1, le=86400),
    seed: int | None = Query(None),
    anomaly_rate: float = Query(0.0, ge=0.0, le=1.0),
    asset_id: str | None = Query(None, max_length=64),
) -> dict[str, Any]:
    product, sensor = _lookup(product_id, sensor_id)
    return _mock_response(
        product, sensor, schema.fields, count, interval_s, seed, anomaly_rate, asset_id
    )


@app.get("/api/products/{product_id}/sensors/{sensor_id}/code")
def generator_code(product_id: str, sensor_id: str) -> dict[str, Any]:
    product, sensor = _lookup(product_id, sensor_id)
    return _generator_code(product, sensor, sensor.fields, inspect.getsource(mock_data))


@app.post("/api/products/{product_id}/sensors/{sensor_id}/code")
def custom_generator_code(
    product_id: str, sensor_id: str, schema: SensorFieldSchema
) -> dict[str, Any]:
    product, sensor = _lookup(product_id, sensor_id)
    fields = schema.fields
    fields_literal = pprint.pformat([_generator_spec(f) for f in fields], width=110, sort_dicts=False)
    curl = (
        f"curl -X POST \"$API_URL/api/products/{product.id}/sensors/{sensor.id}/mock?count=10&seed=42\" "
        "-H 'content-type: application/json' "
        f"--data {shlex.quote(json.dumps({'fields': [field.model_dump(exclude_none=True) for field in fields]}))}\n"
    )
    return _generator_code(product, sensor, fields, inspect.getsource(mock_custom_data), curl, fields_literal)


def _generator_code(
    product: Product,
    sensor: SensorSpec,
    fields: list[FieldSpec],
    api_source: str,
    curl: str | None = None,
    fields_literal: str | None = None,
) -> dict[str, Any]:
    if fields_literal is None:
        fields_literal = pprint.pformat([_generator_spec(f) for f in fields], width=110, sort_dicts=False)
    standalone = (
        GENERATOR_SOURCE.rstrip()
        + "\n\n\n# ---------------------------------------------------------------------------\n"
        + f"# Sensor spec: {product.name} -> {sensor.name}\n"
        + "# ---------------------------------------------------------------------------\n"
        + f"SENSOR_ID = {sensor.id!r}\n"
        + f"ASSET_ID = {_asset_id(product.id)!r}\n"
        + f"INTERVAL_S = {sensor.sample_interval_s}\n"
        + f"FIELDS = {fields_literal}\n\n\n"
        + "if __name__ == \"__main__\":\n"
        + "    import argparse\n"
        + "    import json\n\n"
        + "    parser = argparse.ArgumentParser(description=\"Generate mock readings\")\n"
        + "    parser.add_argument(\"--count\", type=int, default=10)\n"
        + "    parser.add_argument(\"--seed\", type=int, default=None)\n"
        + "    parser.add_argument(\"--anomaly-rate\", type=float, default=0.0)\n"
        + "    args = parser.parse_args()\n"
        + "    data = generate_readings(SENSOR_ID, FIELDS, asset_id=ASSET_ID, count=args.count,\n"
        + "                             interval_s=INTERVAL_S, seed=args.seed, anomaly_rate=args.anomaly_rate)\n"
        + "    print(json.dumps(data, indent=2, ensure_ascii=False))\n"
    )
    if curl is None:
        curl = f"curl \"$API_URL/api/products/{product.id}/sensors/{sensor.id}/mock?count=10&seed=42\"\n"
    return {
        "files": [
            {"filename": f"generate_{sensor.id.replace('-', '_')}.py", "language": "python", "content": standalone},
            {"filename": "backend/app/main.py (API route)", "language": "python", "content": api_source},
            {"filename": "curl.sh", "language": "bash", "content": curl},
        ]
    }
