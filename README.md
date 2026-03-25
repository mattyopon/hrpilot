# HRPilot

AI-powered HR consulting SaaS - 人事コンサルAI

## Features

1. **人事制度設計AI** - 企業規模・業種に基づく等級制度・報酬制度の自動設計
2. **労務コンプライアンスチェック** - 労働基準法・安全衛生法等の法令遵守チェック
3. **採用計画AI** - 事業計画からの必要人員算出、チャネル推奨、JD自動生成
4. **評価制度設計AI** - MBO/OKR/コンピテンシー評価のテンプレート生成
5. **就業規則チェックAI** - 法定記載事項の充足確認、ハラスメント防止・テレワーク規定チェック

## Tech Stack

- **Backend**: Python / FastAPI
- **Frontend**: Streamlit
- **Database**: SQLite
- **Testing**: pytest

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
# API server
uvicorn app.main:app --reload

# Streamlit UI
streamlit run ui/streamlit_app.py
```

## Test

```bash
python3 -m pytest tests/ -q
```

## Project Structure

```
app/
  models.py              # データモデル
  main.py                # FastAPI エンドポイント
  db/database.py         # SQLite データベース
  services/
    hr_system_designer.py    # 人事制度設計
    labor_compliance.py      # 労務コンプライアンス
    recruitment_planner.py   # 採用計画
    evaluation_designer.py   # 評価制度設計
    rules_checker.py         # 就業規則チェック
  knowledge/
    hr_frameworks.py         # 等級・評価フレームワーク
    labor_laws.py            # 労働関連法令
    compliance_checklist.py  # コンプライアンスチェックリスト
tests/                   # テスト (153 tests)
ui/streamlit_app.py      # Streamlit UI
```

## PilotStack

Part of the [PilotStack](https://github.com/mattyopon) suite of AI-powered consulting tools.

---

(c) 2026 PilotStack
