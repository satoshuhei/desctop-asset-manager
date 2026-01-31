# Test Cases

## TC-001: App startup smoke
- Purpose: Verify the GUI can start without exception.
- Preconditions: Tk available on environment.
- Steps:
  1. Launch `DesktopApp` with a temporary DB path.
  2. Call `update_idletasks()` and `update()` once.
  3. Destroy the root window.
- Expected: No exception is raised.
- Automated: tests/test_app_startup.py::test_app_startup_smoke

## TC-002: DB init smoke
- Purpose: Verify database initialization completes.
- Preconditions: None.
- Steps:
  1. Call `init_db(":memory:")`.
  2. Close the connection.
- Expected: No exception is raised.
- Automated: tests/test_db_smoke.py::test_init_db_smoke

## TC-003: Sample data seeding
- Purpose: Verify sample device and license data are created when tables are empty.
- Preconditions: Empty in-memory DB.
- Steps:
  1. Call `init_db(":memory:")`.
  2. Query counts from `devices` and `licenses` tables.
- Expected: Both counts are greater than 0.
- Automated: tests/test_db_smoke.py::test_init_db_seeds_sample_data

## TC-004: Import smoke
- Purpose: Verify module imports work with configured paths.
- Preconditions: None.
- Steps:
  1. Import `main`.
  2. Import `dam.ui.desktop.app`.
- Expected: No exception is raised.
- Automated: tests/test_imports.py::test_imports
