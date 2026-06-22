# なぞなぞ世界モデル

https://github.com/bonsai/nazo-world

> 日本語なぞなぞ **1048問** から構築した世界モデル。
> 同音異義語ネットワーク・ダジャレテンプレート・推論法則の構造分析。

---

## 📂 構成

```
nazo-world/
├── paper/          # 4P論文 (理論編)
│   └── nazo_world_paper.md
├── report/         # 分析レポート
│   └── world_model_report.md
├── data/           # データ
│   ├── riddles_raw.json    # 1048問 生データ
│   ├── world_model.json    # 6層 知識グラフ
│   ├── nazo_world.db       # SQLite (9テーブル)
│   └── csv/                # BQ-ready CSV
├── src/            # 生成・分析スクリプト
│   ├── generate_riddles.py
│   ├── fill_riddles_v2.py
│   ├── fill_riddles_v3.py
│   ├── to_bq_format.py
│   └── ...
└── viz/            # 可視化
```

## 📊 データ

| テーブル | 行数 | 説明 |
|---------|------|------|
| riddles | 1048 | 問題・答え・カテゴリ |
| entities | 753 | 登場エンティティ |
| riddle_entities | 3236 | 問題×エンティティリンク |
| entity_relations | 350 | エンティティ間関係 |
| homophone_groups | 54 | 同音異義語グループ |
| wordplay_templates | 9 | テンプレートパターン |
| reasoning_laws | 14 | 推論法則 |
| categories | 10 | カテゴリ定義 |

## 🔬 主要な発見

1. **「XXはXXでもXXないXXは？」** テンプレートが **48%** を占める
2. **同音異義語の3大パターン**: 食べ物⇄道具 / 体の部位 / 動物⇄干支
3. **日本語の同音異義語ネットワーク**: 753エンティティ・54グループ
4. **14の推論法則**: なぞなぞ世界の生成規則

## 📤 BigQuery インポート

```bash
for f in data/csv/*.csv; do
  table=\$(basename \$f .csv)
  bq load --source_format=CSV --autodetect your_dataset.\${table} \${f}
done
```

## 📄 ライセンス

MIT

