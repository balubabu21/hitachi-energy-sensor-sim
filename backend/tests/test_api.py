import subprocess
import sys
import json

from fastapi.testclient import TestClient

from app import catalog
from app.main import app

client = TestClient(app)


def test_products_listed():
    r = client.get("/api/products")
    assert r.status_code == 200
    assert len(r.json()) == len(catalog.PRODUCTS)


def test_every_sensor_generates_values_within_range():
    for p in catalog.PRODUCTS:
        for s in p.sensors:
            r = client.get(f"/api/products/{p.id}/sensors/{s.id}/mock", params={"count": 50, "seed": 1, "anomaly_rate": 0.2})
            assert r.status_code == 200, (p.id, s.id)
            readings = r.json()["readings"]
            assert len(readings) == 50
            for f in s.fields:
                for rd in readings:
                    v = rd["values"][f.name]
                    vals = list(v.values()) if isinstance(v, dict) else [v]
                    for x in vals:
                        if f.dtype in ("float", "integer", "float_array"):
                            assert f.min <= x <= f.max, (p.id, s.id, f.name, x)
                        if f.dtype == "enum":
                            assert x in f.options


def test_seed_is_deterministic_for_values():
    url = "/api/products/power-transformer/sensors/dga-monitor/mock"
    a = client.get(url, params={"seed": 7}).json()["readings"]
    b = client.get(url, params={"seed": 7}).json()["readings"]
    assert [x["values"] for x in a] == [x["values"] for x in b]


def test_counter_is_monotonic():
    r = client.get("/api/products/hv-switchgear/sensors/breaker-mechanism/mock", params={"count": 100, "seed": 3})
    counts = [x["values"]["operation_count"] for x in r.json()["readings"]]
    assert counts == sorted(counts)


def test_code_panel_script_runs_standalone(tmp_path):
    files = client.get("/api/products/energy-storage/sensors/bms-rack/code").json()["files"]
    script = tmp_path / files[0]["filename"]
    script.write_text(files[0]["content"])
    out = subprocess.run([sys.executable, "-I", str(script), "--count", "3", "--seed", "1"],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    assert len(data) == 3 and "state_of_charge" in data[0]["values"]


def test_unknown_product_404():
    assert client.get("/api/products/nope").status_code == 404
    assert client.get("/api/products/hvdc/sensors/nope/mock").status_code == 404
