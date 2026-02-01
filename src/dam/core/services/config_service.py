from __future__ import annotations

from typing import List

from dam.core.domain.models import Configuration, Device, License
from dam.infra.repositories import ConfigRepository


class ConfigService:
    def __init__(self, config_repo: ConfigRepository) -> None:
        self._config_repo = config_repo

    def create_config(self, name: str, note: str = "", config_no: str | None = None) -> Configuration:
        return self._config_repo.create(name=name, note=note, config_no=config_no)

    def list_configs(self) -> List[Configuration]:
        return self._config_repo.list_all()

    def rename_config(self, config_id: int, name: str) -> None:
        self._config_repo.rename(config_id, name)

    def list_config_devices(self, config_id: int) -> List[Device]:
        return self._config_repo.list_devices(config_id)

    def list_config_licenses(self, config_id: int) -> List[License]:
        return self._config_repo.list_licenses(config_id)

    def list_assigned_device_ids(self) -> List[int]:
        return self._config_repo.list_assigned_device_ids()

    def list_assigned_license_ids(self) -> List[int]:
        return self._config_repo.list_assigned_license_ids()

    def get_device_owner(self, device_id: int) -> int | None:
        return self._config_repo.get_device_owner(device_id)

    def get_license_owner(self, license_id: int) -> int | None:
        return self._config_repo.get_license_owner(license_id)

    def assign_device(self, config_id: int, device_id: int) -> None:
        self._config_repo.assign_device(config_id, device_id)

    def move_device(self, from_config_id: int, to_config_id: int, device_id: int) -> None:
        self._config_repo.move_device(from_config_id, to_config_id, device_id)

    def unassign_device(self, config_id: int, device_id: int) -> None:
        self._config_repo.unassign_device(config_id, device_id)

    def assign_license(self, config_id: int, license_id: int) -> None:
        self._config_repo.assign_license(config_id, license_id)

    def unassign_license(self, config_id: int, license_id: int) -> None:
        self._config_repo.unassign_license(config_id, license_id)
