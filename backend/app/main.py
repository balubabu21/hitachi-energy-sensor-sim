"""FastAPI application exposing the product/sensor catalogue and mock data."""
from __future__ import annotations

import inspect
import os
import pprint
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import catalog
from .generator import generate_readings
from .models import FieldSpec

app = FastAPI(
    title="Hitachi Energy Sensor Simulator API",
    version="1.0.0",
    description="Mock sensor data for Hitachi Energy product families (simulation only).",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])

GENERATOR_SOURCE = (Path(__file__).parent / "generator.py").read_text(encoding="utf-8")
GENERATOR_KEYS = ("name", "dtype", "min", "max", "nominal", "precision", "options", "p_true", "labels", "step")


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    interval = interval_s or sensor.sample_interval_s
    readings = generate_readings(
        sensor.id,
        [_generator_spec(f) for f in sensor.fields],
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


@app.get("/api/products/{product_id}/sensors/{sensor_id}/code")
def generator_code(product_id: str, sensor_id: str) -> dict[str, Any]:
    product, sensor = _lookup(product_id, sensor_id)
    fields_literal = pprint.pformat([_generator_spec(f) for f in sensor.fields], width=110, sort_dicts=False)
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
    api_source = inspect.getsource(mock_data)
    curl = (
        f"curl \"$API_URL/api/products/{product.id}/sensors/{sensor.id}/mock?count=10&seed=42\"\n"
    )
    return {
        "files": [
            {"filename": f"generate_{sensor.id.replace('-', '_')}.py", "language": "python", "content": standalone},
            {"filename": "backend/app/main.py (API route)", "language": "python", "content": api_source},
            {"filename": "curl.sh", "language": "bash", "content": curl},
        ]
    }
