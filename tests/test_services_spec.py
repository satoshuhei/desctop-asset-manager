from __future__ import annotations

import os
import sys

import pytest


def _ensure_src_path() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(root, "src")
    if root not in sys.path:
        sys.path.insert(0, root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_path()

from dam.core.services.asset_service import AssetService  # noqa: E402
from dam.core.services.config_service import ConfigService  # noqa: E402
from dam.infra.db import init_db  # noqa: E402
from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository  # noqa: E402


def _build_services() -> tuple[AssetService, ConfigService]:
    conn = init_db(":memory:")
    device_repo = DeviceRepository(conn)
    license_repo = LicenseRepository(conn)
    config_repo = ConfigRepository(conn)
    return AssetService(device_repo, license_repo), ConfigService(config_repo)


def test_device_create_and_list() -> None:
    asset_service, _ = _build_services()

    device = asset_service.add_device(
        asset_no="DEV-900",
        display_name="Spec Device",
        device_type="PC",
        model="Model X",
        version="v1",
        state="active",
        note="spec",
    )

    devices = asset_service.list_devices()
    assert device in devices


def test_license_create_and_list() -> None:
    asset_service, _ = _build_services()

    license_item = asset_service.add_license(
        license_no="LIC-900",
        name="Spec License",
        license_key="LIC-900",
        state="active",
        note="spec",
    )

    licenses = asset_service.list_licenses()
    assert license_item in licenses


def test_config_create_rename_list() -> None:
    _, config_service = _build_services()

    config = config_service.create_config(name="Config A")
    assert config.created_at
    assert config.updated_at
    config_service.rename_config(config.config_id, "Config A1")

    configs = config_service.list_configs()
    assert any(c.config_id == config.config_id and c.name == "Config A1" for c in configs)


def test_assign_and_move_device_between_configs() -> None:
    asset_service, config_service = _build_services()

    device = asset_service.add_device(
        asset_no="DEV-901",
        display_name="Move Device",
        device_type="Laptop",
        model="Model Y",
        version="v2",
        state="active",
        note="spec",
    )
    config_a = config_service.create_config(name="Config A")
    config_b = config_service.create_config(name="Config B")

    config_service.assign_device(config_a.config_id, device.device_id)
    devices_a = config_service.list_config_devices(config_a.config_id)
    assert any(d.device_id == device.device_id for d in devices_a)

    config_service.move_device(config_a.config_id, config_b.config_id, device.device_id)
    devices_a_after = config_service.list_config_devices(config_a.config_id)
    devices_b = config_service.list_config_devices(config_b.config_id)
    assert all(d.device_id != device.device_id for d in devices_a_after)
    assert any(d.device_id == device.device_id for d in devices_b)


def test_assign_device_rejects_second_config() -> None:
    asset_service, config_service = _build_services()

    device = asset_service.add_device(
        asset_no="DEV-902",
        display_name="Unique Device",
        device_type="Laptop",
        model="Model Z",
        version="v3",
        state="active",
        note="spec",
    )
    config_a = config_service.create_config(name="Config A")
    config_b = config_service.create_config(name="Config B")

    config_service.assign_device(config_a.config_id, device.device_id)
    with pytest.raises(ValueError):
        config_service.assign_device(config_b.config_id, device.device_id)


def test_assign_and_unassign_license() -> None:
    asset_service, config_service = _build_services()

    license_item = asset_service.add_license(
        license_no="LIC-901",
        name="Spec License 2",
        license_key="LIC-901",
        state="active",
        note="spec",
    )
    config = config_service.create_config(name="Config C")

    config_service.assign_license(config.config_id, license_item.license_id)
    licenses = config_service.list_config_licenses(config.config_id)
    assert any(l.license_id == license_item.license_id for l in licenses)

    config_service.unassign_license(config.config_id, license_item.license_id)
    licenses_after = config_service.list_config_licenses(config.config_id)
    assert all(l.license_id != license_item.license_id for l in licenses_after)
