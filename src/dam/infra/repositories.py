from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

from dam.core.domain.models import Configuration, Device, License


class DeviceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _row_to_device(row: tuple) -> Device:
        return Device(*row)

    def create(
        self,
        asset_no: str,
        display_name: Optional[str],
        device_type: str,
        model: str,
        version: str,
        state: str,
        note: str,
    ) -> Device:
        cur = self._conn.execute(
            """
            INSERT INTO devices (asset_no, display_name, device_type, model, version, state, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_no, display_name, device_type, model, version, state, note),
        )
        self._conn.commit()
        return self.get_by_id(int(cur.lastrowid))

    def list_all(self) -> List[Device]:
        cur = self._conn.execute(
            """
            SELECT device_id, asset_no, display_name, device_type, model, version, state, note
            FROM devices
            ORDER BY device_id DESC
            """
        )
        return [self._row_to_device(row) for row in cur.fetchall()]

    def get_by_id(self, device_id: int) -> Device:
        cur = self._conn.execute(
            """
            SELECT device_id, asset_no, display_name, device_type, model, version, state, note
            FROM devices
            WHERE device_id = ?
            """,
            (device_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Device not found")
        return self._row_to_device(row)


class LicenseRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _row_to_license(row: tuple) -> License:
        return License(*row)

    def create(self, name: str, license_key: str, state: str, note: str) -> License:
        cur = self._conn.execute(
            """
            INSERT INTO licenses (name, license_key, state, note)
            VALUES (?, ?, ?, ?)
            """,
            (name, license_key, state, note),
        )
        self._conn.commit()
        return self.get_by_id(int(cur.lastrowid))

    def list_all(self) -> List[License]:
        cur = self._conn.execute(
            """
            SELECT license_id, name, license_key, state, note
            FROM licenses
            ORDER BY license_id DESC
            """
        )
        return [self._row_to_license(row) for row in cur.fetchall()]

    def get_by_id(self, license_id: int) -> License:
        cur = self._conn.execute(
            """
            SELECT license_id, name, license_key, state, note
            FROM licenses
            WHERE license_id = ?
            """,
            (license_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("License not found")
        return self._row_to_license(row)


class ConfigRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _row_to_config(row: tuple) -> Configuration:
        return Configuration(*row)

    def create(self, name: str, note: str, config_no: Optional[str] = None) -> Configuration:
        if config_no is None:
            next_id = self._conn.execute("SELECT COALESCE(MAX(config_id), 0) + 1 FROM configurations").fetchone()[0]
            config_no = f"CNFG-{int(next_id):03d}"
        cur = self._conn.execute(
            """
            INSERT INTO configurations (config_no, name, note)
            VALUES (?, ?, ?)
            """,
            (config_no, name, note),
        )
        self._conn.commit()
        return self.get_by_id(int(cur.lastrowid))

    def list_all(self) -> List[Configuration]:
        cur = self._conn.execute(
            """
            SELECT config_id, config_no, name, note
            FROM configurations
            ORDER BY config_id ASC
            """
        )
        return [self._row_to_config(row) for row in cur.fetchall()]

    def get_by_id(self, config_id: int) -> Configuration:
        cur = self._conn.execute(
            """
            SELECT config_id, config_no, name, note
            FROM configurations
            WHERE config_id = ?
            """,
            (config_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Configuration not found")
        return self._row_to_config(row)

    def rename(self, config_id: int, name: str) -> None:
        self._conn.execute(
            """
            UPDATE configurations
            SET name = ?
            WHERE config_id = ?
            """,
            (name, config_id),
        )
        self._conn.commit()

    def list_devices(self, config_id: int) -> List[Device]:
        cur = self._conn.execute(
            """
            SELECT d.device_id, d.asset_no, d.display_name, d.device_type, d.model, d.version, d.state, d.note
            FROM devices d
            INNER JOIN config_devices cd ON cd.device_id = d.device_id
            WHERE cd.config_id = ?
            ORDER BY d.device_id DESC
            """,
            (config_id,),
        )
        return [Device(*row) for row in cur.fetchall()]

    def list_licenses(self, config_id: int) -> List[License]:
        cur = self._conn.execute(
            """
            SELECT l.license_id, l.name, l.license_key, l.state, l.note
            FROM licenses l
            INNER JOIN config_licenses cl ON cl.license_id = l.license_id
            WHERE cl.config_id = ?
            ORDER BY l.license_id DESC
            """,
            (config_id,),
        )
        return [License(*row) for row in cur.fetchall()]

    def assign_device(self, config_id: int, device_id: int) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO config_devices (config_id, device_id)
            VALUES (?, ?)
            """,
            (config_id, device_id),
        )
        self._conn.commit()

    def unassign_device(self, config_id: int, device_id: int) -> None:
        self._conn.execute(
            """
            DELETE FROM config_devices
            WHERE config_id = ? AND device_id = ?
            """,
            (config_id, device_id),
        )
        self._conn.commit()

    def move_device(self, from_config_id: int, to_config_id: int, device_id: int) -> None:
        if from_config_id == to_config_id:
            return
        self.unassign_device(from_config_id, device_id)
        self.assign_device(to_config_id, device_id)

    def assign_license(self, config_id: int, license_id: int, note: str = "") -> None:
        self._conn.execute(
            """
            INSERT INTO config_licenses (config_id, license_id, note)
            VALUES (?, ?, ?)
            ON CONFLICT(license_id) DO UPDATE SET config_id = excluded.config_id
            """,
            (config_id, license_id, note),
        )
        self._conn.commit()

    def unassign_license(self, config_id: int, license_id: int) -> None:
        self._conn.execute(
            """
            DELETE FROM config_licenses
            WHERE config_id = ? AND license_id = ?
            """,
            (config_id, license_id),
        )
        self._conn.commit()
