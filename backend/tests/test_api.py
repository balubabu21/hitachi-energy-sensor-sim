import subprocess
import sys
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import catalog
from app import main
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


def test_custom_schema_updates_generated_values_without_mutating_catalog(tmp_path):
    url = "/api/products/power-transformer/sensors/thermal-monitor"
    schema = {
        "fields": [
            {
                "name": "top_oil_temp",
                "dtype": "float",
                "min": 50,
                "max": 60,
                "nominal": 55,
                "precision": 1,
                "description": "Adjusted top-oil range",
            },
            {
                "name": "custom_voltage",
                "dtype": "integer",
                "min": 100,
                "max": 120,
                "nominal": 110,
                "precision": 0,
                "description": "Custom voltage measurement",
            },
            {
                "name": "custom_condition",
                "dtype": "enum",
                "options": {"NORMAL": 0.9, "ALARM": 0.1},
                "description": "Custom condition classification",
            },
        ]
    }

    response = client.post(
        f"{url}/mock", params={"count": 20, "seed": 4, "anomaly_rate": 1}, json=schema
    )
    assert response.status_code == 200
    for reading in response.json()["readings"]:
        assert set(reading["values"]) == {"top_oil_temp", "custom_voltage", "custom_condition"}
        assert 50 <= reading["values"]["top_oil_temp"] <= 60
        assert 100 <= reading["values"]["custom_voltage"] <= 120
        assert reading["values"]["custom_condition"] in {"NORMAL", "ALARM"}

    default_response = client.get(f"{url}/mock", params={"count": 1, "seed": 4})
    assert set(default_response.json()["readings"][0]["values"]) == {
        field.name for field in catalog.get_sensor("power-transformer", "thermal-monitor")[1].fields
    }

    code = client.post(f"{url}/code", json=schema)
    assert code.status_code == 200
    files = code.json()["files"]
    script = tmp_path / files[0]["filename"]
    script.write_text(files[0]["content"])
    output = subprocess.run(
        [sys.executable, "-I", str(script), "--count", "2", "--seed", "1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert set(json.loads(output)[0]["values"]) == {
        "top_oil_temp", "custom_voltage", "custom_condition"
    }
    assert "custom_voltage" in files[2]["content"]


def test_custom_schema_rejects_invalid_fields():
    url = "/api/products/power-transformer/sensors/thermal-monitor/mock"
    invalid_range = {
        "fields": [
            {
                "name": "temperature",
                "dtype": "float",
                "min": 20,
                "max": 10,
                "nominal": 15,
                "description": "Invalid range",
            }
        ]
    }
    assert client.post(url, json=invalid_range).status_code == 422

    duplicate_names = {
        "fields": [
            {"name": "same", "dtype": "boolean", "p_true": 0.1, "description": "First"},
            {"name": "same", "dtype": "boolean", "p_true": 0.2, "description": "Second"},
        ]
    }
    assert client.post(url, json=duplicate_names).status_code == 422

    assert client.post(url, json={"fields": []}).status_code == 422


def test_sensor_submission_sends_review_email(monkeypatch):
    sent_messages = []

    class FakePoller:
        def result(self, timeout=None):
            return {"status": "Succeeded"}

    class FakeEmailClient:
        @classmethod
        def from_connection_string(cls, connection_string):
            assert connection_string == "test-connection"
            return cls()

        def begin_send(self, message):
            sent_messages.append(message)
            return FakePoller()

        def close(self):
            pass

    monkeypatch.setattr(main, "EmailClient", FakeEmailClient)
    monkeypatch.setenv("ACS_EMAIL_CONNECTION_STRING", "test-connection")
    monkeypatch.setenv("ACS_EMAIL_SENDER_ADDRESS", "sensor-review@example.com")
    request = {
        "product_id": "power-transformer",
        "product_name": "Power Transformers",
        "sensor": {
            "id": "local-oil-quality",
            "name": "Oil quality sensor",
            "description": "Browser-created sensor",
            "principle": "Synthetic measurement",
            "protocol": "Browser-only",
            "sample_interval_s": 30,
            "fields": [{
                "name": "water_content",
                "dtype": "float",
                "description": "Water content",
                "min": 0,
                "max": 80,
                "nominal": 12,
                "precision": 1,
            }],
        },
        "submitter_name": "Example Submitter",
        "submitter_email": "submitter@example.com",
        "approver_email": "reviewer@hitachienergy.com",
    }

    response = client.post("/api/sensor-requests", json=request)

    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    message = sent_messages[0]
    assert message["recipients"]["to"] == [{"address": "balu.babu@method.com"}]
    assert message["content"]["subject"].endswith("local-oil-quality")
    assert "submitter@example.com" in message["content"]["plainText"]
    assert "reviewer@hitachienergy.com" in message["content"]["plainText"]
    assert "Power Transformers (power-transformer)" in message["content"]["plainText"]
    assert "water_content" in message["content"]["plainText"]


def test_sensor_submission_requires_hitachi_energy_approver(monkeypatch):
    monkeypatch.setenv("ACS_EMAIL_CONNECTION_STRING", "test-connection")
    monkeypatch.setenv("ACS_EMAIL_SENDER_ADDRESS", "sensor-review@example.com")
    request = {
        "product_id": "power-transformer",
        "product_name": "Power Transformers",
        "sensor": {
            "id": "local-sensor",
            "name": "Sensor",
            "description": "Browser-created sensor",
            "principle": "Synthetic",
            "protocol": "Browser-only",
            "sample_interval_s": 60,
            "fields": [{
                "name": "value",
                "dtype": "boolean",
                "description": "Value",
                "p_true": 0.5,
            }],
        },
        "submitter_name": "Example Submitter",
        "submitter_email": "submitter@example.com",
        "approver_email": "reviewer@hitachienergy.com.attacker.test",
    }
    response = client.post("/api/sensor-requests", json=request)
    assert response.status_code == 422


def test_sensor_submission_reports_missing_azure_email_configuration(monkeypatch):
    monkeypatch.delenv("ACS_EMAIL_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("ACS_EMAIL_SENDER_ADDRESS", raising=False)
    request = {
        "product_id": "power-transformer",
        "product_name": "Power Transformers",
        "sensor": {
            "id": "local-sensor",
            "name": "Sensor",
            "description": "Browser-created sensor",
            "principle": "Synthetic",
            "protocol": "Browser-only",
            "sample_interval_s": 60,
            "fields": [{
                "name": "value",
                "dtype": "boolean",
                "description": "Value",
                "p_true": 0.5,
            }],
        },
        "submitter_name": "Example Submitter",
        "submitter_email": "submitter@example.com",
        "approver_email": "reviewer@hitachienergy.com",
    }
    response = client.post("/api/sensor-requests", json=request)
    assert response.status_code == 503


def test_sensor_submission_rate_limit():
    main._sensor_request_times.clear()
    submitter = "rate-limit-test@example.com"
    for _ in range(main.SENSOR_REQUEST_LIMIT):
        main._check_sensor_request_rate(submitter)
    with pytest.raises(HTTPException) as error:
        main._check_sensor_request_rate(submitter)
    assert error.value.status_code == 429
    main._sensor_request_times.clear()


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
