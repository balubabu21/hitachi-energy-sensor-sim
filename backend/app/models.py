"""Domain models for the sensor catalogue.

A Product (e.g. a power transformer) carries several Sensors (e.g. a DGA
monitor). Each Sensor emits readings made of Fields. A Field spec describes
the data type, unit, physical range and a nominal operating value, which the
mock generator uses to produce realistic readings.
"""
from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel, Field as PField, field_validator, model_validator

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
    name: str = PField(min_length=1, max_length=64, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    dtype: DataType
    description: str = PField(min_length=1, max_length=500)
    unit: str | None = PField(default=None, max_length=32)
    min: float | None = None
    max: float | None = None
    nominal: float | None = None
    precision: int = PField(default=2, ge=0, le=12)
    # enum: value -> relative weight
    options: dict[str, float] | None = None
    # boolean: probability of True
    p_true: float | None = None
    # float_array: labels of each element (e.g. phases L1, L2, L3)
    labels: list[str] | None = None
    # counter: maximum increment per sample
    step: int | None = None

    @model_validator(mode="after")
    def validate_values(self) -> FieldSpec:
        numeric_values = (self.min, self.max, self.nominal)
        if any(value is not None and not math.isfinite(value) for value in numeric_values):
            raise ValueError("Numeric field values must be finite")

        if self.dtype in ("float", "integer", "counter", "float_array"):
            if self.min is None or self.max is None or self.nominal is None:
                raise ValueError("Numeric fields require min, max, and nominal values")
            if self.min > self.max:
                raise ValueError("min must not exceed max")
            if not self.min <= self.nominal <= self.max:
                raise ValueError("nominal must be within the field range")

        if self.dtype in ("integer", "counter") and any(
            value is not None and not value.is_integer() for value in numeric_values
        ):
            raise ValueError("Integer and counter ranges and nominal values must be integers")

        if self.dtype == "counter" and (self.step is None or self.step < 1):
            raise ValueError("Counter fields require a positive step")

        if self.dtype == "boolean":
            if self.p_true is None or not math.isfinite(self.p_true) or not 0 <= self.p_true <= 1:
                raise ValueError("Boolean fields require p_true between 0 and 1")

        if self.dtype == "enum":
            if not self.options or any(
                not math.isfinite(weight) or weight < 0 for weight in self.options.values()
            ) or sum(self.options.values()) <= 0:
                raise ValueError("Enum fields require non-negative option weights with a positive total")
            if len(self.options) > 100 or any(not option or len(option) > 64 for option in self.options):
                raise ValueError("Enum fields support at most 100 options of up to 64 characters each")

        if self.dtype == "float_array" and (
            not self.labels or any(not label.strip() for label in self.labels)
            or any(len(label) > 64 for label in self.labels)
            or len(set(self.labels)) != len(self.labels) or len(self.labels) > 100
        ):
            raise ValueError("Array fields require up to 100 unique, non-empty labels of at most 64 characters")

        return self

    @property
    def json_type(self) -> str:
        return JSON_TYPE[self.dtype]


class SensorFieldSchema(BaseModel):
    fields: list[FieldSpec] = PField(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_field_names(self) -> SensorFieldSchema:
        names = [field.name for field in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("Field names must be unique")
        if {"timestamp", "asset_id", "sensor_id", "sequence", "quality"}.intersection(names):
            raise ValueError("Field names cannot replace envelope fields")
        return self


class SensorSpec(BaseModel):
    id: str = PField(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = PField(min_length=1, max_length=120, pattern=r"^[^\r\n\t]+$")
    description: str = PField(min_length=1, max_length=1000)
    principle: str = PField(
        min_length=1, max_length=500, description="Measurement principle / sensor technology"
    )
    protocol: str = PField(min_length=1, max_length=120, description="Typical communication protocol")
    sample_interval_s: int = PField(default=60, ge=1, le=86400)
    fields: list[FieldSpec] = PField(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_field_names(self) -> SensorSpec:
        names = [field.name for field in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("Field names must be unique")
        if {"timestamp", "asset_id", "sensor_id", "sequence", "quality"}.intersection(names):
            raise ValueError("Field names cannot replace envelope fields")
        if {"timestamp", "asset_id", "sensor_id", "sequence", "quality"}.intersection(names):
            raise ValueError("Field names cannot replace envelope fields")
        return self


_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


class SensorSubmission(BaseModel):
    product_id: str = PField(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    product_name: str = PField(min_length=1, max_length=120, pattern=r"^[^\r\n\t]+$")
    sensor: SensorSpec
    submitter_name: str = PField(min_length=1, max_length=120)
    submitter_email: str = PField(min_length=3, max_length=254)
    approver_email: str = PField(min_length=3, max_length=254)

    @model_validator(mode="after")
    def validate_browser_sensor(self) -> SensorSubmission:
        if not self.sensor.id.startswith("local-"):
            raise ValueError("Only browser-created sensors can be submitted")
        return self

    @field_validator("submitter_name")
    @classmethod
    def validate_submitter_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Submitter name must be non-empty and contain no control characters")
        return value

    @field_validator("submitter_email", "approver_email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        value = value.strip()
        if not _EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("approver_email")
    @classmethod
    def validate_approver_domain(cls, value: str) -> str:
        if value.rsplit("@", 1)[-1].lower() != "hitachienergy.com":
            raise ValueError("Approver email must use the @hitachienergy.com domain")
        return value


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
