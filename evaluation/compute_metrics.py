import csv, math
from collections import defaultdict

import os

PAIRS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'controlled_ranking_pairs.csv')
METHODS = [
    ('tfidf_score', 'TF-IDF only'),
    ('embedding_score', 'Embedding similarity only'),
    ('skill_score', 'Skill coverage only'),
    ('proposed_score', 'Proposed full score'),
]

def dcg(rels, k):
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels[:k]))

def ndcg(rels, k):
    ideal = sorted(rels, reverse=True)
    denom = dcg(ideal, k)
    return dcg(rels, k) / denom if denom else 0.0

rows = []
with open(PAIRS_FILE, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        row['relevance'] = int(row['relevance'])
        for score_col, _ in METHODS:
            row[score_col] = float(row[score_col])
        rows.append(row)
by_query = defaultdict(list)
for row in rows:
    by_query[row['query_id']].append(row)

print("| Method | Mean NDCG@10 | Mean NDCG@20 | Precision@10 (rel>=2) | MRR (rel>=2) |")
print("| :--- | :---: | :---: | :---: | :---: |")
for score_col, name in METHODS:
    vals = []
    for qid, qrows in by_query.items():
        ranked = sorted(qrows, key=lambda r: r[score_col], reverse=True)
        rels = [r['relevance'] for r in ranked]
        p10 = sum(1 for r in rels[:10] if r >= 2) / 10
        rr = next((1 / rank for rank, r in enumerate(rels, 1) if r >= 2), 0)
        vals.append((ndcg(rels, 10), ndcg(rels, 20), p10, rr))
    mean = [sum(x[i] for x in vals) / len(vals) for i in range(4)]
    print(f'| {name} | {mean[0]:.3f} | {mean[1]:.3f} | {mean[2]:.3f} | {mean[3]:.3f} |')
