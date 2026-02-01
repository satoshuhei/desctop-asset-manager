from __future__ import annotations

from typing import List, Optional

from dam.core.domain.models import Device, License
from dam.infra.repositories import DeviceRepository, LicenseRepository


class AssetService:
    def __init__(self, device_repo: DeviceRepository, license_repo: LicenseRepository) -> None:
        self._device_repo = device_repo
        self._license_repo = license_repo

    def add_device(
        self,
        asset_no: str,
        display_name: Optional[str],
        device_type: str,
        model: str,
        version: str,
        state: str,
        note: str,
    ) -> Device:
        return self._device_repo.create(
            asset_no=asset_no,
            display_name=display_name,
            device_type=device_type,
            model=model,
            version=version,
            state=state,
            note=note,
        )

    def list_devices(self) -> List[Device]:
        return self._device_repo.list_all()

    def add_license(self, license_no: str, name: str, license_key: str, state: str, note: str) -> License:
        return self._license_repo.create(
            license_no=license_no,
            name=name,
            license_key=license_key,
            state=state,
            note=note,
        )

    def list_licenses(self) -> List[License]:
        return self._license_repo.list_all()
