#!/usr/bin/env python3
"""
Convert riddle world model data to SQLite + CSV (BigQuery-ready).
Normalized schema for fast querying and easy BQ import.
"""
import json, csv, sqlite3, os

BASE = "/mnt/c/Users/dance/Documents/MEGA"
DB_PATH = os.path.join(BASE, "nazo_world.db")

# ── Load data ──
with open(os.path.join(BASE, "riddles_raw.json"), "r", encoding="utf-8") as f:
    riddles_data = json.load(f)

with open(os.path.join(BASE, "world_model.json"), "r", encoding="utf-8") as f:
    wm = json.load(f)

riddles = riddles_data["riddles"]

# ── Connect / create DB ──
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")
conn.execute("PRAGMA journal_mode = WAL;")
c = conn.cursor()

# ── Schema ──
c.executescript("""
CREATE TABLE riddles (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT DEFAULT 'generated',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    riddle_count INTEGER DEFAULT 0
);

CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    frequency INTEGER DEFAULT 1,
    aliases TEXT
);

CREATE TABLE riddle_entities (
    riddle_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    role TEXT DEFAULT 'mentioned',
    PRIMARY KEY (riddle_id, entity_id),
    FOREIGN KEY (riddle_id) REFERENCES riddles(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY,
    source_entity TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    strength INTEGER DEFAULT 1
);

CREATE TABLE homophone_groups (
    id INTEGER PRIMARY KEY,
    word TEXT NOT NULL,
    meaning TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    group_id INTEGER
);

CREATE TABLE wordplay_templates (
    id INTEGER PRIMARY KEY,
    pattern TEXT UNIQUE NOT NULL,
    frequency INTEGER DEFAULT 1,
    description TEXT
);

CREATE TABLE reasoning_laws (
    id INTEGER PRIMARY KEY,
    law_text TEXT NOT NULL,
    category TEXT,
    examples_count INTEGER DEFAULT 0
);

CREATE TABLE ontology (
    id INTEGER PRIMARY KEY,
    parent TEXT NOT NULL,
    child TEXT NOT NULL,
    relation_type TEXT DEFAULT 'contains',
    UNIQUE(parent, child)
);

CREATE INDEX idx_riddles_cat ON riddles(category);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_relations_src ON entity_relations(source_entity);
CREATE INDEX idx_homophones_word ON homophone_groups(word);
""")

# ── 1. Insert riddles ──
print("📦 riddles...")
cat_counts = {}
for i, r in enumerate(riddles):
    c.execute("INSERT INTO riddles (id, question, answer, category) VALUES (?,?,?,?)",
              (i, r["q"], r["a"], r["cat"]))
    cat_counts[r["cat"]] = cat_counts.get(r["cat"], 0) + 1

# ── 2. Insert categories ──
print("📦 categories...")
for name, cnt in sorted(cat_counts.items()):
    c.execute("INSERT INTO categories (name, riddle_count) VALUES (?,?)", (name, cnt))

# ── 3. Insert entities ──
print("📦 entities...")
entity_map = wm.get("entity_map", {})
entity_id_map = {}
for idx, (ename, edata) in enumerate(sorted(entity_map.items(), key=lambda x: -x[1].get("count", 0))):
    cats = ",".join(edata.get("categories", []))
    aliases = ",".join(edata.get("aliases", [])) if isinstance(edata.get("aliases"), list) else str(edata.get("aliases", ""))
    c.execute("INSERT INTO entities (id, name, category, frequency, aliases) VALUES (?,?,?,?,?)",
              (idx, ename, cats, edata.get("count", 1), aliases))
    entity_id_map[ename] = idx

# ── 4. Link riddles ↔ entities ──
print("📦 riddle_entities (linking)...")
for idx, r in enumerate(riddles):
    qa_text = r["q"] + r["a"]
    for ename in entity_map:
        if ename in qa_text:
            eid = entity_id_map.get(ename)
            if eid is not None:
                try:
                    c.execute("INSERT OR IGNORE INTO riddle_entities (riddle_id, entity_id) VALUES (?,?)",
                              (idx, eid))
                except:
                    pass

# ── 5. Insert entity_relations ──
print("📦 entity_relations...")
relations = wm.get("entity_relations", [])
for rel in relations:
    c.execute("""INSERT INTO entity_relations (source_entity, target_entity, relation_type, strength)
                 VALUES (?,?,?,?)""",
              (rel.get("source", ""), rel.get("target", ""),
               rel.get("relation", ""), rel.get("strength", 1)))

# ── 6. Insert homophone groups ──
print("📦 homophone_groups...")
hmap = wm.get("homophone_map", [])
if isinstance(hmap, list):
    for gid, group in enumerate(hmap):
        word = group.get("word", "")
        homophones = group.get("homophones", [])
        if isinstance(homophones, list):
            for h in homophones:
                c.execute("INSERT INTO homophone_groups (word, meaning, frequency, group_id) VALUES (?,?,?,?)",
                          (word, h.get("meaning", ""), h.get("count", 1), gid))
        else:
            c.execute("INSERT INTO homophone_groups (word, meaning, frequency, group_id) VALUES (?,?,?,?)",
                      (word, str(homophones), 1, gid))
elif isinstance(hmap, dict):
    for gid, (word, groups) in enumerate(hmap.items()):
        if isinstance(groups, list):
            for h in groups:
                c.execute("INSERT INTO homophone_groups (word, meaning, frequency, group_id) VALUES (?,?,?,?)",
                          (word, h.get("meaning", ""), h.get("count", 1), gid))

# ── 7. Insert wordplay templates ──
print("📦 wordplay_templates...")
templates = wm.get("wordplay_patterns", {}).get("templates", [])
for tp in templates:
    c.execute("INSERT INTO wordplay_templates (pattern, frequency, description) VALUES (?,?,?)",
              (tp.get("pattern", ""), tp.get("count", 1), tp.get("description", "")))

# ── 8. Insert reasoning laws ──
print("📦 reasoning_laws...")
laws = wm.get("reasoning_laws", [])
for lid, law in enumerate(laws):
    c.execute("INSERT INTO reasoning_laws (id, law_text, examples_count) VALUES (?,?,?)",
              (lid, law, 1))

# ── 9. Insert ontology ──
print("📦 ontology...")
onto = wm.get("ontology", {})
if isinstance(onto, dict):
    for parent, data in onto.items():
        children = data.get("children", []) if isinstance(data, dict) else []
        if isinstance(children, list):
            for child in children:
                try:
                    c.execute("INSERT OR IGNORE INTO ontology (parent, child) VALUES (?,?)",
                              (parent, child))
                except:
                    pass

conn.commit()

# ══════════════════════════════════════════════════
# Export to CSV
# ══════════════════════════════════════════════════
print("\n📤 Exporting CSVs...")
tables = [
    "riddles", "categories", "entities",
    "riddle_entities", "entity_relations",
    "homophone_groups", "wordplay_templates",
    "reasoning_laws", "ontology"
]

csv_dir = os.path.join(BASE, "csv_exports")
os.makedirs(csv_dir, exist_ok=True)

for table in tables:
    cursor = conn.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    csv_path = os.path.join(csv_dir, f"{table}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(rows)
    print(f"   {table}.csv: {len(rows)} rows")

conn.close()

# ══════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"✅ データベース:      {DB_PATH}")
print(f"   サイズ:           {os.path.getsize(DB_PATH)/1024:.0f} KB")
print(f"✅ CSVエクスポート:   {csv_dir}/")
for table in tables:
    fp = os.path.join(csv_dir, f"{table}.csv")
    rows = sum(1 for _ in open(fp, encoding="utf-8")) - 1  # -1 for header
    print(f"   {table:25s} {rows:>5} rows")
print(f"{'='*50}")
print("BQインポート: bq load --source_format=CSV ... csv_exports/*.csv")
