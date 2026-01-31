from __future__ import annotations

import sqlite3


def _seed_sample_data(conn: sqlite3.Connection) -> None:
    device_count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    if device_count == 0:
        conn.executemany(
            """
            INSERT INTO devices (asset_no, display_name, device_type, model, version, state, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("DEV-001", "Office PC", "PC", "OptiPlex 7090", "2023", "active", "sample"),
                ("DEV-002", "Meeting Laptop", "Laptop", "ThinkPad X1", "Gen 10", "active", "sample"),
            ],
        )

    license_count = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
    if license_count == 0:
        conn.executemany(
            """
            INSERT INTO licenses (name, license_key, state, note)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("Office 365", "O365-SAMPLE-001", "active", "sample"),
                ("Adobe CC", "ADCC-SAMPLE-001", "active", "sample"),
            ],
        )


def init_db(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_no TEXT UNIQUE NOT NULL,
            display_name TEXT,
            device_type TEXT NOT NULL,
            model TEXT NOT NULL,
            version TEXT NOT NULL,
            state TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS licenses (
            license_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license_key TEXT NOT NULL,
            state TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS configurations (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config_devices (
            config_id INTEGER NOT NULL,
            device_id INTEGER NOT NULL,
            PRIMARY KEY (config_id, device_id),
            FOREIGN KEY (config_id) REFERENCES configurations(config_id)
                ON DELETE CASCADE,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
                ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config_licenses (
            config_id INTEGER NOT NULL,
            license_id INTEGER NOT NULL UNIQUE,
            note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (config_id, license_id),
            FOREIGN KEY (config_id) REFERENCES configurations(config_id)
                ON DELETE CASCADE,
            FOREIGN KEY (license_id) REFERENCES licenses(license_id)
                ON DELETE CASCADE
        )
        """
    )

    _seed_sample_data(conn)
    conn.commit()
    return conn
