# テスト資料構成とテスト対象対応表

## 1. 目的
本書は、テストで使用する資料（テスト資材）と、対応するコード範囲を整理し、網羅性と追跡性を確保することを目的とする。

## 2. テスト資材一覧
- テスト戦略書: docs/test_strategy/test_strategy.md
- テストカバー範囲: docs/test_strategy/test_coverage.md
- テスト項目詳細: docs/test_strategy/test_items_detail.md
- 本書（テスト資材↔コード対応表）: docs/test_strategy/test_docs_and_mapping.md
- テストケース（既存）: docs/test_cases.md
- テスト設計（既存）: docs/test_design.puml
- トレーサビリティ（既存）: docs/traceability.md

## 3. テスト資材↔コード対応表（詳細）
### 3.1 サービス層
| テスト資材 | テストファイル | テスト対象コード |
|---|---|---|
| テスト戦略書 | tests/test_services_spec.py | src/dam/core/services/asset_service.py | 
| テスト戦略書 | tests/test_services_spec.py | src/dam/core/services/config_service.py |
| テスト項目詳細 | tests/test_services_spec.py | src/dam/infra/repositories.py（ConfigRepository） |
| テストカバー範囲 | tests/test_detail_specs.py | src/dam/infra/repositories.py（使用中制約） |

### 3.2 DB 初期化・シード
| テスト資材 | テストファイル | テスト対象コード |
|---|---|---|
| テスト戦略書 | tests/test_db_smoke.py | src/dam/infra/db.py |
| テスト項目詳細 | tests/test_db_smoke.py | src/dam/infra/db.py（スキーマ／シード） |

### 3.3 UI（Qt）
| テスト資材 | テストファイル | テスト対象コード |
|---|---|---|
| テストカバー範囲 | tests/test_ui_spec.py | src/dam/ui/desktop/app.py（DevicePanel） |
| テストカバー範囲 | tests/test_ui_spec.py | src/dam/ui/desktop/app.py（LicensePanel） |
| テスト項目詳細 | tests/test_ui_spec.py | src/dam/ui/desktop/app.py（ConfigCanvasWidget） |
| テスト項目詳細 | tests/test_ui_spec.py | src/dam/ui/desktop/app.py（ConfigCardWidget） |

### 3.4 起動・インポート
| テスト資材 | テストファイル | テスト対象コード |
|---|---|---|
| テスト戦略書 | tests/test_app_startup.py | src/dam/ui/desktop/app.py（起動経路） |
| テストカバー範囲 | tests/test_imports.py | src/dam/**（import 可能性） |

## 4. テスト観点別の対応
### 4.1 機能観点
- 作成・一覧: AssetService / DeviceRepository / LicenseRepository
- 割り当て・解除: ConfigService / ConfigRepository / UIActions
- 使用中制約: ConfigRepository / DevicePanel / LicensePanel
- UI 表示: ConfigCanvasWidget / DevicePanel / LicensePanel

### 4.2 非機能観点（範囲内）
- 例外時の挙動: ConfigRepository（ValueError）
- 既定ソート・フィルタ: DevicePanel / LicensePanel
- シード妥当性: init_db

## 5. テストドキュメント構成（一般形）
### 5.1 戦略
- 目的・範囲・方針
- テスト階層と責務
- リスクと優先度

### 5.2 設計
- テスト観点と分類
- テストデータ方針
- 環境・ツール

### 5.3 仕様
- テスト項目詳細
- 入力・期待値・判定基準
- 例外系の期待挙動

### 5.4 実装
- テストコード配置
- 命名規約
- 実行手順

### 5.5 管理
- トレーサビリティ
- 変更履歴
- レビュー基準

## 6. 既存ドキュメントへの適用
- 戦略: docs/test_strategy/test_strategy.md
- カバー範囲: docs/test_strategy/test_coverage.md
- 項目詳細: docs/test_strategy/test_items_detail.md
- 設計図: docs/test_design.puml
- トレーサビリティ: docs/traceability.md

## 7. 運用ルール
- 仕様変更時は対応テストと資材を同時更新
- テスト追加時は本対応表に追記
- 変更後は pytest -q を実行
