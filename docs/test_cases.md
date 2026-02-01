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

## TC-005: Config card drag position
- Purpose: Verify configuration cards can be moved within the canvas.
- Preconditions: Tk available on environment.
- Steps:
  1. Create a configuration board with two configs.
  2. Simulate a drag on Config A.
  3. Verify the stored position changed.
- Expected: The position for Config A updates after drag.
- Automated: tests/test_ui_config_board_drag.py::test_config_board_drag_updates_position

## TC-006: Config No auto generation
- Purpose: Verify configuration numbers are generated from the next config id.
- Preconditions: Initialized DB with existing configurations.
- Steps:
  1. Query the next config id from the DB.
  2. Create a configuration without specifying a config number.
  3. Compare the generated config number to the expected format.
- Expected: config_no equals CNFG-XXX for the next id.
- Automated: tests/test_detail_specs.py::test_config_no_auto_generation

## TC-007: License assignment moves between configurations
- Purpose: Verify a license can belong to only one configuration at a time.
- Preconditions: Two configurations and one license.
- Steps:
  1. Assign the license to Config A.
  2. Assign the same license to Config B.
  3. List licenses for both configs.
- Expected: The license appears only under Config B.
- Automated: tests/test_detail_specs.py::test_assign_license_moves_to_new_config

## TC-008: UI state position persistence
- Purpose: Verify canvas positions and hidden state are persisted.
- Preconditions: Writable UI state DB path.
- Steps:
  1. Save hidden flag and position for configs.
  2. Reload the store and read positions.
- Expected: Stored positions and hidden flags are preserved.
- Automated: tests/test_detail_specs.py::test_ui_state_store_positions_and_hidden

## TC-009: UI canvas state roundtrip
- Purpose: Verify zoom/center state persists between sessions.
- Preconditions: Writable UI state DB path.
- Steps:
  1. Save a canvas state.
  2. Reload the store and read the canvas state.
- Expected: The loaded canvas state matches the saved state.
- Automated: tests/test_detail_specs.py::test_ui_state_store_canvas_state_roundtrip
