"""Domain models for the sensor catalogue.

A Product (e.g. a power transformer) carries several Sensors (e.g. a DGA
monitor). Each Sensor emits readings made of Fields. A Field spec describes
the data type, unit, physical range and a nominal operating value, which the
mock generator uses to produce realistic readings.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field as PField

DataType = Literal["float", "integer", "counter", "boolean", "enum", "float_array"]

# How each internal data type is represented in the emitted JSON.
JSON_TYPE: dict[str, str] = {
    "float": "number",
    "integer": "integer",
    "counter": "integer (monotonic)",
    "boolean": "boolean",
    "enum": "string (enum)",
    "float_array": "object<label, number>",
}


class FieldSpec(BaseModel):
    name: str
    dtype: DataType
    description: str
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    nominal: float | None = None
    precision: int = 2
    # enum: value -> relative weight
    options: dict[str, float] | None = None
    # boolean: probability of True
    p_true: float | None = None
    # float_array: labels of each element (e.g. phases L1, L2, L3)
    labels: list[str] | None = None
    # counter: maximum increment per sample
    step: int | None = None

    @property
    def json_type(self) -> str:
        return JSON_TYPE[self.dtype]


class SensorSpec(BaseModel):
    id: str
    name: str
    description: str
    principle: str = PField(description="Measurement principle / sensor technology")
    protocol: str = PField(description="Typical communication protocol")
    sample_interval_s: int = 60
    fields: list[FieldSpec]


class Product(BaseModel):
    id: str
    name: str
    group: str
    description: str
    url: str
    examples: list[str] = []
    sensors: list[SensorSpec]


# ---------------------------------------------------------------------------
# Small builder helpers that keep catalog.py readable
# ---------------------------------------------------------------------------

def num(name: str, unit: str | None, lo: float, hi: float, nom: float, desc: str, prec: int = 2) -> FieldSpec:
    return FieldSpec(name=name, dtype="float", unit=unit, min=lo, max=hi, nominal=nom, description=desc, precision=prec)


def integer(name: str, unit: str | None, lo: int, hi: int, nom: int, desc: str) -> FieldSpec:
    return FieldSpec(name=name, dtype="integer", unit=unit, min=lo, max=hi, nominal=nom, description=desc, precision=0)


def counter(name: str, unit: str | None, start: int, hi: int, step: int, desc: str) -> FieldSpec:
    return FieldSpec(name=name, dtype="counter", unit=unit, min=start, max=hi, nominal=start, step=step, description=desc, precision=0)


def flag(name: str, desc: str, p: float = 0.02) -> FieldSpec:
    return FieldSpec(name=name, dtype="boolean", p_true=p, description=desc)


def enum(name: str, options: dict[str, float], desc: str) -> FieldSpec:
    return FieldSpec(name=name, dtype="enum", options=options, description=desc)


def phases(name: str, unit: str | None, lo: float, hi: float, nom: float, desc: str, prec: int = 2,
           labels: tuple[str, ...] = ("L1", "L2", "L3")) -> FieldSpec:
    return FieldSpec(name=name, dtype="float_array", unit=unit, min=lo, max=hi, nominal=nom,
                     description=desc, precision=prec, labels=list(labels))
