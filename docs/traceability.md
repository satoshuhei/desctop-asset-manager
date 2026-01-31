# Traceability

## Requirements to Tests
| Requirement | Tests |
| --- | --- |
| RQ-001 | tests/test_app_startup.py::test_app_startup_smoke |
| RQ-002 | tests/test_imports.py::test_imports |
| RQ-003 | tests/test_imports.py::test_imports |
| RQ-004 | tests/test_imports.py::test_imports |
| RQ-005 | tests/test_imports.py::test_imports |
| RQ-006 | tests/test_imports.py::test_imports |
| RQ-007 | tests/test_imports.py::test_imports |
| RQ-008 | tests/test_db_smoke.py::test_init_db_seeds_sample_data |
| RQ-009 | tests/test_app_startup.py::test_app_startup_smoke |
| RQ-010 | tests/test_ui_config_board_drag.py::test_config_board_drag_updates_position |
| RN-001 | tests/test_imports.py::test_imports |
| RN-002 | tests/test_app_startup.py::test_app_startup_smoke, tests/test_db_smoke.py::test_init_db_seeds_sample_data |

## Tests to Basic Design
| Test | Design Elements |
| --- | --- |
| tests/test_app_startup.py::test_app_startup_smoke | DesktopApp, init_db |
| tests/test_db_smoke.py::test_init_db_smoke | init_db |
| tests/test_db_smoke.py::test_init_db_seeds_sample_data | init_db |
| tests/test_imports.py::test_imports | DesktopApp, DeviceListView, LicenseListView, ConfigBoard |
| tests/test_ui_config_board_drag.py::test_config_board_drag_updates_position | ConfigBoard |
