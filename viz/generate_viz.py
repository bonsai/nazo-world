#!/usr/bin/env python3
"""Visualization: entity correlation network, category pie, homophone cluster."""
import json, sqlite3, os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "nazo_world.db")
WM = os.path.join(BASE, "data", "world_model.json")
OUT = os.path.join(BASE, "viz")

os.makedirs(OUT, exist_ok=True)
conn = sqlite3.connect(DB)

# ── 1. Category pie (matplotlib text) ──
cat = conn.execute("SELECT name, riddle_count FROM categories ORDER BY riddle_count DESC").fetchall()
total = sum(r for _, r in cat)
pie_lines = ["# カテゴリ分布\n"]
for name, cnt in cat:
    pct = cnt / total * 100
    bar = "█" * int(pct / 2)
    pie_lines.append(f"  {name:15s} {bar} {cnt:>4} ({pct:5.1f}%)")
with open(os.path.join(OUT, "category_distribution.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(pie_lines))

# ── 2. Homophone cluster (text + JSON) ──
homophones = conn.execute("SELECT word, meaning, frequency, group_id FROM homophone_groups ORDER BY group_id, frequency DESC").fetchall()
groups = {}
for word, meaning, freq, gid in homophones:
    groups.setdefault(gid, []).append((word, meaning, freq))
cluster_lines = ["# 同音異義語クラスター\n"]
for gid, members in groups.items():
    cluster_lines.append(f"\n## Group {gid}: {members[0][0]}")
    for word, meaning, freq in members:
        cluster_lines.append(f"  {word:10s} → {meaning:15s} ({freq}回)")
with open(os.path.join(OUT, "homophone_clusters.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(cluster_lines))

# ── 3. Entity network (D3.js JSON) ──
ents = conn.execute("SELECT id, name, frequency FROM entities WHERE frequency >= 3 ORDER BY frequency DESC").fetchall()
rels = conn.execute("SELECT source_entity, target_entity, strength FROM entity_relations WHERE strength >= 2").fetchall()
ent_ids = {name: eid for eid, name, _ in ents}
nodes = [{"id": eid, "name": name, "freq": freq, "size": freq * 2} for eid, name, freq in ents]
links = []
for src, tgt, strength in rels:
    if src in ent_ids and tgt in ent_ids:
        links.append({"source": ent_ids[src], "target": ent_ids[tgt], "strength": strength})
d3_data = {"nodes": nodes, "links": links}
with open(os.path.join(OUT, "entity_network.json"), "w", encoding="utf-8") as f:
    json.dump(d3_data, f, ensure_ascii=False, indent=2)

# ── 4. Reasoning laws ──
laws = conn.execute("SELECT id, law_text FROM reasoning_laws").fetchall()
law_lines = ["# なぞなぞ世界の14法則\n"]
for lid, text in laws:
    law_lines.append(f"\n### 法則{lid+1}")
    law_lines.append(f"{text}")
with open(os.path.join(OUT, "reasoning_laws.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(law_lines))

conn.close()

print("✅ Viz files generated:")
for fn in os.listdir(OUT):
    fp = os.path.join(OUT, fn)
    print(f"   {fn:40s} {os.path.getsize(fp):>6}B")
