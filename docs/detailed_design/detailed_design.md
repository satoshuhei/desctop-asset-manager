# 詳細設計書

## 1. 概要
本書は基本設計書に対応した詳細設計です。責務分担、データスキーマ、操作挙動、使用中（In-Use）制約を含む割り当て制御を具体化します。

## 2. 対象範囲
- Qt ベースのデスクトップ UI
- サービス／リポジトリ実装
- SQLite スキーマとシードデータ
- 割り当てバリデーションと UI フィードバック

## 3. アーキテクチャ
### 3.1 レイヤ構成
- UI 層：アセットパレット／構成キャンバス／ログの各ウィジェット。
- サービス層：AssetService／ConfigService のオーケストレーション。
- リポジトリ層：SQLite アクセスと割り当て制御。
- ストレージ層：SQLite データベースとシードデータ。

### 3.2 主要コンポーネント
- DesktopApp：サービスと UI を結線し、更新をトリガー。
- AssetPaletteWidget：DevicePanel／LicensePanel を内包。
- DevicePanel／LicensePanel：フィルタ・ソート・ドラッグ元・使用中表示。
- ConfigCanvasWidget：キャンバス、カード、ドラッグ先、選択とログ。
- ConfigCardWidget：構成単位の一覧とコンテキストメニュー。
- LogPanel：ユーザー操作ログ。

## 4. データモデル
### 4.1 テーブル
- devices(device_id PK, asset_no UNIQUE, display_name, device_type, model, version, state, note)
- licenses(license_id PK, license_no, name, license_key, state, note)
- configurations(config_id PK, config_no, name, note, created_at, updated_at)
- config_devices(config_id FK, device_id FK, PK(config_id, device_id))
- config_licenses(config_id FK, license_id FK UNIQUE, note, PK(config_id, license_id))

### 4.2 使用中制約（導出）
- 使用中デバイス：config_devices に device_id が存在。
- 使用中ライセンス：config_licenses に license_id が存在。

## 5. UI 設計
### 5.1 アセットパレット
- フィルタ：キーワード／種別／状態（デバイス）、キーワード／状態（ライセンス）。
- ソート：資産番号／ライセンス番号の降順が既定。
- 使用中表示：
  - 行をグレー表示。
  - 使用中はドラッグ不可。
  - ツールチップで使用中を明示。

### 5.2 構成キャンバス
- カードに割り当て済みアセットを表示（デバイスは表、ライセンスはリスト）。
- パレットからカードへドラッグ＆ドロップ。
- コンテキストメニューで割り当て解除。
- 整列ボタンで構成番号／日時の並び替え。

### 5.3 ログパネル
- 操作メッセージと競合はタイムスタンプ付きで追記。

## 6. サービス設計
### 6.1 AssetService
- add_device(asset_no, display_name, device_type, model, version, state, note)
- list_devices()
- add_license(license_no, name, license_key, state, note)
- list_licenses()

### 6.2 ConfigService
- create_config(name, note, config_no?)
- list_configs()
- rename_config(config_id, name)
- assign_device(config_id, device_id)
- unassign_device(config_id, device_id)
- move_device(from_config_id, to_config_id, device_id)
- assign_license(config_id, license_id)
- unassign_license(config_id, license_id)
- list_assigned_device_ids()
- list_assigned_license_ids()
- get_device_owner(device_id)
- get_license_owner(license_id)

## 7. リポジトリ設計
### 7.1 DeviceRepository／LicenseRepository
- create, list_all, get_by_id

### 7.2 ConfigRepository
- list_devices(config_id)
- list_licenses(config_id)
- assign_device(config_id, device_id)
  - 他構成に割り当て済みの場合は拒否。
- assign_license(config_id, license_id)
  - 他構成に割り当て済みの場合は拒否。
- list_assigned_device_ids(), list_assigned_license_ids()
- get_device_owner(device_id), get_license_owner(license_id)

## 8. 操作フロー
### 8.1 デバイス割り当て
1. パレットからデバイスをドラッグ。
2. 使用中のデバイスはドラッグ不可。
3. リポジトリで所有権を検証して登録。
4. UI を更新し、操作／拒否をログに記録。

### 8.2 ライセンス割り当て
1. パレットからライセンスをドラッグ。
2. 使用中のライセンスはドラッグ不可。
3. リポジトリで所有権を検証して登録。
4. UI を更新し、操作／拒否をログに記録。

## 9. サンプルデータ
- テーブルが空の場合のみシードデータを作成。
- 使用中制約を満たす一意な割り当てを生成。

## 10. エラーハンドリング
- 割り当て競合はリポジトリで ValueError。
- UI はトースト／ログで通知。

## 11. ログ
- 割り当て／解除／競合をログに記録。
