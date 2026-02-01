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
                ("DEV-001", "ECU解析ワークステーション", "PC", "Precision 3660", "2024", "active", "sample"),
                ("DEV-002", "車載ログ収集ノート", "Laptop", "ThinkPad P1", "Gen 6", "active", "sample"),
                ("DEV-003", "CANインターフェース", "Interface", "Vector VN1610", "v2", "active", "sample"),
                ("DEV-004", "CAN-FDインターフェース", "Interface", "Vector VN1630A", "v1", "active", "sample"),
                ("DEV-005", "J2534パススルー", "Interface", "DrewTech MongoosePro", "v3", "active", "sample"),
                ("DEV-006", "車載電源供給", "Power", "BK Precision 1901B", "2022", "active", "sample"),
                ("DEV-007", "オシロスコープ", "Instrument", "Keysight DSOX1102G", "2021", "active", "sample"),
                ("DEV-008", "車載ネットワークアダプタ", "Interface", "Kvaser Leaf Light", "v2", "active", "sample"),
                ("DEV-009", "ECUベンチハーネス", "Harness", "Custom Bench", "2024", "active", "sample"),
                ("DEV-010", "ECUリプロ/フラッシャ", "Programmer", "ETAS ES953", "v2", "active", "sample"),
            ],
        )

    license_count = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
    if license_count == 0:
        conn.executemany(
            """
            INSERT INTO licenses (license_no, name, license_key, state, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("LIC-001", "CANape", "CANAPE-SAMPLE-001", "active", "sample"),
                ("LIC-002", "CANalyzer", "CANA-SAMPLE-002", "active", "sample"),
                ("LIC-003", "CANoe", "CANOE-SAMPLE-003", "active", "sample"),
                ("LIC-004", "INCA Base", "INCA-SAMPLE-004", "active", "sample"),
                ("LIC-005", "INCA AddOn ASAP2", "INCA-SAMPLE-005", "active", "sample"),
                ("LIC-006", "Vector vMeasure", "VMEASURE-SAMPLE-006", "active", "sample"),
                ("LIC-007", "ETAS MDA", "ETAS-SAMPLE-007", "active", "sample"),
                ("LIC-008", "ETAS ASCMO", "ETAS-SAMPLE-008", "active", "sample"),
                ("LIC-009", "Diag Studio", "DIAG-SAMPLE-009", "active", "sample"),
                ("LIC-010", "Flash Tool", "FLASH-SAMPLE-010", "active", "sample"),
            ],
        )

    config_count = conn.execute("SELECT COUNT(*) FROM configurations").fetchone()[0]
    if config_count == 0:
        conn.executemany(
            """
            INSERT INTO configurations (config_no, name, note)
            VALUES (?, ?, ?)
            """,
            [
                ("CNFG-001", "ECU解析-エンジン", "sample"),
                ("CNFG-002", "ECU解析-トランスミッション", "sample"),
                ("CNFG-003", "ECU解析-ブレーキ", "sample"),
                ("CNFG-004", "ECU解析-ADAS", "sample"),
                ("CNFG-005", "ECU解析-ボディ", "sample"),
                ("CNFG-006", "ECU解析-インフォテインメント", "sample"),
                ("CNFG-007", "ECU解析-電源管理", "sample"),
                ("CNFG-008", "ECU解析-テレマティクス", "sample"),
            ],
        )

    config_device_count = conn.execute("SELECT COUNT(*) FROM config_devices").fetchone()[0]
    config_license_count = conn.execute("SELECT COUNT(*) FROM config_licenses").fetchone()[0]
    if config_device_count == 0 and config_license_count == 0:
        config_ids = [row[0] for row in conn.execute("SELECT config_id FROM configurations ORDER BY config_id")]
        device_ids = [row[0] for row in conn.execute("SELECT device_id FROM devices ORDER BY device_id")]
        license_ids = [row[0] for row in conn.execute("SELECT license_id FROM licenses ORDER BY license_id")]

        device_pairs = []
        license_pairs = []
        for index, config_id in enumerate(config_ids):
            if index < len(device_ids):
                device_pairs.append((config_id, device_ids[index]))
            license_id = license_ids[index % len(license_ids)]
            license_pairs.append((config_id, license_id, "sample"))

        conn.executemany(
            """
            INSERT OR IGNORE INTO config_devices (config_id, device_id)
            VALUES (?, ?)
            """,
            device_pairs,
        )
        conn.executemany(
            """
            INSERT INTO config_licenses (config_id, license_id, note)
            VALUES (?, ?, ?)
            ON CONFLICT(license_id) DO UPDATE SET config_id = excluded.config_id
            """,
            license_pairs,
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
            license_no TEXT NOT NULL,
            name TEXT NOT NULL,
            license_key TEXT NOT NULL,
            state TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    _ensure_license_no(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS configurations (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_no TEXT,
            name TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_config_no(conn)
    _ensure_config_timestamps(conn)
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


def _ensure_config_no(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(configurations)")]
    if "config_no" not in columns:
        conn.execute("ALTER TABLE configurations ADD COLUMN config_no TEXT")
    conn.execute(
        """
        UPDATE configurations
        SET config_no = printf('CNFG-%03d', config_id)
        WHERE config_no IS NULL OR config_no = ''
        """
    )


def _ensure_config_timestamps(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(configurations)")]
    if "created_at" not in columns:
        conn.execute("ALTER TABLE configurations ADD COLUMN created_at TEXT")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE configurations ADD COLUMN updated_at TEXT")
    conn.execute(
        """
        UPDATE configurations
        SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
        WHERE created_at IS NULL OR created_at = '' OR updated_at IS NULL OR updated_at = ''
        """
    )


def _ensure_license_no(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(licenses)")]
    if "license_no" not in columns:
        conn.execute("ALTER TABLE licenses ADD COLUMN license_no TEXT")
    conn.execute(
        """
        UPDATE licenses
        SET license_no = printf('LIC-%03d', license_id)
        WHERE license_no IS NULL OR license_no = ''
        """
    )
