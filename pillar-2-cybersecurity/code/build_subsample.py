"""
Build the stratified CWE-category subsample for Pillar 2.

Key design decision (discovered during data inspection): PrimeVul's individual
splits are too CWE-sparse on their own (91.9% of test.jsonl vulnerable records
have no CWE tag at all). Combining train+valid+test pools 6,968 vulnerable
records, of which 2,727 (39.1%) carry a CWE tag across 93 categories. Since we
are doing our own independent zero-shot evaluation (not reusing PrimeVul's
fine-tuning train/test split for its intended purpose), pooling all splits is
methodologically fine here.

For each of the top-N most frequent CWE categories, we sample:
  - up to K vulnerable examples tagged with that CWE
  - a matched patched/benign counterpart from the paired data where available
    (same CWE context, high textual similarity -- the "hard" comparison),
    else a random benign example as a fallback.
"""
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "primevul_full"
OUT_DIR = Path(__file__).parent.parent / "data"
SEED = 20260729
TOP_N_CATEGORIES = 15
K_PER_CATEGORY = 15


def cwe_list(r):
    cwe = r.get("cwe")
    if not cwe:
        return []
    if isinstance(cwe, str):
        return [cwe]
    return list(cwe)


def load(path):
    recs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def main():
    rng = random.Random(SEED)

    general = (
        load(DATA_DIR / "primevul_train.jsonl")
        + load(DATA_DIR / "primevul_valid.jsonl")
        + load(DATA_DIR / "primevul_test.jsonl")
    )
    paired = (
        load(DATA_DIR / "primevul_train_paired.jsonl")
        + load(DATA_DIR / "primevul_valid_paired.jsonl")
        + load(DATA_DIR / "primevul_test_paired.jsonl")
    )

    # Index paired data by (project, commit_id) to find vulnerable/patched pairs
    paired_by_commit = defaultdict(list)
    for r in paired:
        paired_by_commit[(r["project"], r["commit_id"])].append(r)

    vuln_with_cwe = [r for r in general if r["target"] == 1 and cwe_list(r)]
    cwe_counts = Counter()
    for r in vuln_with_cwe:
        cwe_counts.update(cwe_list(r))
    top_categories = [c for c, _ in cwe_counts.most_common(TOP_N_CATEGORIES)]

    by_category = defaultdict(list)
    for r in vuln_with_cwe:
        for c in cwe_list(r):
            if c in top_categories:
                by_category[c].append(r)

    benign_pool = [r for r in general if r["target"] == 0]

    sample_rows = []
    for category in top_categories:
        candidates = by_category[category]
        rng.shuffle(candidates)
        chosen = candidates[:K_PER_CATEGORY]
        for vr in chosen:
            key = (vr["project"], vr["commit_id"])
            pair_group = paired_by_commit.get(key, [])
            patched = next((p for p in pair_group if p["target"] == 0), None)
            benign_source = "paired_patch"
            if patched is None:
                patched = rng.choice(benign_pool)
                benign_source = "random_benign"
            sample_rows.append(
                {
                    "cwe_category": category,
                    "vuln_idx": vr["idx"],
                    "vuln_project": vr["project"],
                    "vuln_commit_id": vr["commit_id"],
                    "vuln_func": vr["func"],
                    "vuln_cwe_raw": vr.get("cwe"),
                    "benign_idx": patched["idx"],
                    "benign_source": benign_source,
                    "benign_func": patched["func"],
                }
            )

    out_path = OUT_DIR / "pillar2_subsample.jsonl"
    with open(out_path, "w") as f:
        for row in sample_rows:
            f.write(json.dumps(row))
            f.write("\n")

    print(f"Selected {len(top_categories)} CWE categories: {top_categories}")
    print(f"Total sampled vulnerable+matched-benign pairs: {len(sample_rows)}")
    paired_count = sum(1 for r in sample_rows if r["benign_source"] == "paired_patch")
    print(f"  matched via real paired patch: {paired_count}")
    print(f"  matched via random benign fallback: {len(sample_rows) - paired_count}")
    print(f"Saved to {out_path}")

    # Per-category counts for sanity check
    per_cat = Counter(r["cwe_category"] for r in sample_rows)
    print("Per-category sample sizes:")
    for c in top_categories:
        print(f"  {c}: {per_cat[c]} (available in pool: {len(by_category[c])})")


if __name__ == "__main__":
    main()
