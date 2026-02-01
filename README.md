# desctop-asset-manager

デスクトップ資産管理（Desktop Asset Manager）用のサンプル実装です。端末・ライセンス・割り当て状態を管理するための基本的な構成とテストを含みます。

## 目的
- 資産（デバイス/ライセンス）の登録・参照
- 割り当て状態の管理
- UI/サービス層/永続化層の分離

## 構成
- src/ : アプリ本体
- tests/ : テスト
- docs/ : 設計・テストドキュメント

## 前提
- Python 3.11 以降

## セットアップ
```bash
python -m venv .venv
.venv\Scripts\activate
```

## 実行
```bash
python main.py
```

## テスト
```bash
pytest
```

## ドキュメント
設計やテスト方針は docs/ 配下を参照してください。
