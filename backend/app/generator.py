"""Mock sensor data generator.

This module is deliberately dependency-free (standard library only) so the
UI's code panel can show it verbatim and you can copy it into any script.

Each field spec is a plain dict:
    {"name": "top_oil_temp", "dtype": "float", "min": -40, "max": 130,
     "nominal": 62, "precision": 1}

Supported dtypes:
    float        mean-reverting random walk around `nominal`, clipped to [min, max]
    integer      same as float, rounded to int
    counter      monotonically increasing integer (adds 0..step per sample)
    boolean      True with probability `p_true`
    enum         weighted choice from `options`, "sticky" between samples
    float_array  one random walk per element in `labels` (e.g. phases L1/L2/L3)
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

QUALITY_WEIGHTS = {"GOOD": 0.96, "UNCERTAIN": 0.03, "BAD": 0.01}


def _weighted_choice(rng: random.Random, options: dict[str, float]) -> str:
    keys = list(options)
    return rng.choices(keys, weights=[options[k] for k in keys], k=1)[0]


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class FieldSimulator:
    """Keeps the state of one field so consecutive samples look continuous."""

    THETA = 0.15        # pull back towards nominal per step (mean reversion)
    VOLATILITY = 0.015  # noise as a fraction of the range per step

    def __init__(self, spec: dict[str, Any], rng: random.Random):
        self.spec = spec
        self.rng = rng
        self.state: Any = None
        self.lo = spec.get("min")
        self.hi = spec.get("max")
        self.nominal = spec.get("nominal")
        if self.lo is not None and self.hi is not None:
            self.span = float(self.hi) - float(self.lo)
        else:
            self.span = 1.0

    # -- continuous values ----------------------------------------------------
    def _walk(self, prev: float | None) -> float:
        if prev is None:
            prev = self.nominal + self.rng.gauss(0, self.span * 0.02)
        drift = self.THETA * (self.nominal - prev)
        noise = self.rng.gauss(0, self.span * self.VOLATILITY)
        return _clip(prev + drift + noise, self.lo, self.hi)

    def _anomalous(self) -> float:
        # Push the value to 80-100 % of the way from nominal towards a limit
        target = self.hi if (self.hi - self.nominal) >= (self.nominal - self.lo) else self.lo
        return self.nominal + (target - self.nominal) * self.rng.uniform(0.8, 1.0)

    def next(self, anomaly: bool = False) -> Any:
        s = self.spec
        dtype = s["dtype"]
        prec = s.get("precision", 2)

        if dtype in ("float", "integer"):
            self.state = self._anomalous() if anomaly else self._walk(self.state)
            return int(round(self.state)) if dtype == "integer" else round(self.state, prec)

        if dtype == "float_array":
            labels = s.get("labels") or ["0"]
            if self.state is None:
                self.state = [None] * len(labels)
            self.state = [self._anomalous() if anomaly else self._walk(v) for v in self.state]
            return [round(v, prec) for v in self.state]

        if dtype == "counter":
            if self.state is None:
                self.state = int(s.get("min") or 0)
            step = int(s.get("step") or 1)
            self.state = min(int(s.get("max") or 2**31), self.state + self.rng.randint(0, step))
            return self.state

        if dtype == "boolean":
            p = s.get("p_true", 0.05)
            return True if anomaly else self.rng.random() < p

        if dtype == "enum":
            options: dict[str, float] = s["options"]
            if anomaly:
                # choose the least likely (most "abnormal") state
                return min(options, key=options.get)
            if self.state is None or self.rng.random() > 0.9:
                self.state = _weighted_choice(self.rng, options)
            return self.state

        raise ValueError(f"Unsupported dtype {dtype!r} for field {s['name']}")


def generate_readings(
    sensor_id: str,
    fields: list[dict[str, Any]],
    *,
    asset_id: str = "HE-ASSET-0001",
    count: int = 10,
    interval_s: int = 60,
    seed: int | None = None,
    anomaly_rate: float = 0.0,
    end_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return `count` time-ordered readings for one sensor."""
    rng = random.Random(seed)
    sims = [FieldSimulator(f, rng) for f in fields]
    end = (end_time or datetime.now(timezone.utc)).replace(microsecond=0)
    start = end - timedelta(seconds=interval_s * (count - 1))

    readings: list[dict[str, Any]] = []
    for i in range(count):
        is_anomaly = rng.random() < anomaly_rate
        # an anomaly affects one randomly chosen field
        anomalous_field = rng.randrange(len(sims)) if is_anomaly else -1
        reading: dict[str, Any] = {
            "timestamp": (start + timedelta(seconds=interval_s * i)).isoformat().replace("+00:00", "Z"),
            "asset_id": asset_id,
            "sensor_id": sensor_id,
            "sequence": i,
            "quality": "UNCERTAIN" if is_anomaly else _weighted_choice(rng, QUALITY_WEIGHTS),
        }
        values = {}
        for idx, sim in enumerate(sims):
            value = sim.next(anomaly=(idx == anomalous_field))
            labels = sim.spec.get("labels")
            if sim.spec["dtype"] == "float_array" and labels:
                value = dict(zip(labels, value))
            values[sim.spec["name"]] = value
        reading["values"] = values
        if is_anomaly:
            reading["anomaly"] = {"field": sims[anomalous_field].spec["name"]}
        readings.append(reading)
    return readings
