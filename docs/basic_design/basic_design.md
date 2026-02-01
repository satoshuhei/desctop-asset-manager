# 基本設計書

## 1. 概要
Desktop Asset Manager は、デバイス・ライセンス・構成を管理するデスクトップアプリです。アセットパレット、構成キャンバス、ログパネルを備え、UI／サービス／リポジトリ／SQLite のレイヤー構成で設計されています。

## 2. 対象範囲
- デスクトップ UI（Qt）
- サービス層・リポジトリ層
- SQLite スキーマとサンプルデータ投入
- 使用中（In-Use）制約を含む割り当てルール

## 3. アーキテクチャ
### 3.1 レイヤ構成
- UI 層：Qt ウィジェットと操作
- サービス層：ユースケース調整
- リポジトリ層：SQLite アクセス
- ストレージ層：SQLite データベース

### 3.2 主要コンポーネント
- UI：DesktopApp、AssetPaletteWidget、ConfigCanvasWidget、LogPanel
- サービス：AssetService、ConfigService
- リポジトリ：DeviceRepository、LicenseRepository、ConfigRepository
- ストレージ：SQLite テーブルとシードデータ

## 4. データモデル
### 4.1 エンティティ
- Device：asset_no、display_name、device_type、model、version、state、note
- License：license_no、name、license_key、state、note
- Configuration：config_no、name、note、created_at、updated_at
- ConfigDevice：config_id、device_id
- ConfigLicense：config_id、license_id、note

### 4.2 割り当てルール（使用中制約）
- デバイスは 1 つの構成にのみ割り当て可能。
- ライセンスは 1 つの構成にのみ割り当て可能。

## 5. UI 設計
### 5.1 アセットパレット
- デバイス／ライセンスの一覧（検索・フィルタ）。
- 使用中アセットはグレー表示でドラッグ不可。

### 5.2 構成キャンバス
- 構成カードにデバイス／ライセンス一覧を表示。
- パレットからカードへドラッグ＆ドロップで割り当て。

### 5.3 ログパネル
- 操作ログと競合メッセージを記録。

## 6. サービス設計
- AssetService：デバイス／ライセンスの作成・一覧。
- ConfigService：構成の作成・名称変更・割り当て／解除。

## 7. リポジトリ設計
- デバイス／ライセンス／構成の CRUD。
- 使用中制約の割り当て制御。

## 8. 主要フロー
- パレットからカードへドラッグして割り当て。
- カードのコンテキストメニューで解除。
- 構成カードの整列（並び替え）操作。

## 9. サンプルデータ
- テーブルが空の場合のみサンプルを投入。
- 使用中制約を満たす割り当てにする。

## 10. エラーハンドリング
- 割り当て競合は拒否し、ユーザーへ通知。

## 11. ログ
- 割り当て／解除／競合をログに記録。
