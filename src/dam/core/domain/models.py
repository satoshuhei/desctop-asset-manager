from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Device:
    device_id: int
    asset_no: str
    display_name: Optional[str]
    device_type: str
    model: str
    version: str
    state: str
    note: str


@dataclass(frozen=True)
class License:
    license_id: int
    name: str
    license_key: str
    state: str
    note: str


@dataclass(frozen=True)
class Configuration:
    config_id: int
    config_no: str
    name: str
    note: str


@dataclass(frozen=True)
class ConfigDevice:
    config_id: int
    device_id: int


@dataclass(frozen=True)
class ConfigLicense:
    config_id: int
    license_id: int
    note: str
