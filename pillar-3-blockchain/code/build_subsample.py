"""
Build the Pillar 3 stratified sample from defihack.json (389 real historical
DeFi hacks) + final_dataset (for a general false-positive-rate baseline,
since defihack.json has no patched/safe counterpart per incident).

Multi-label handling: an incident's 'type' field can list several category
tags (e.g. "Dex/AMM, Insufficient validation, Reentrancy"). To avoid
double-counting the same incident into multiple category buckets, we assign
each incident to its FIRST listed tag only as its "primary" category for
stratification purposes -- a simplification, documented as such.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
EVULLM_DIR = Path(__file__).parent.parent / "evullm-original"

SEED = 20260806
TOP_N_CATEGORIES = 8
K_PER_CATEGORY = 12


def primary_category(entry):
    t = entry.get("type") or ""
    tags = [tok.strip() for tok in t.split(",") if tok.strip()]
    return tags[0] if tags else None


def main():
    rng = random.Random(SEED)

    with open(EVULLM_DIR / "defihack.json") as f:
        hacks = json.load(f)
    hacks = [h for h in hacks if h.get("vulnerable_code_snippet")]
    print(f"{len(hacks)} incidents have a usable code snippet")

    by_category = defaultdict(list)
    for h in hacks:
        cat = primary_category(h)
        if cat:
            by_category[cat].append(h)

    top_categories = sorted(by_category, key=lambda c: -len(by_category[c]))[:TOP_N_CATEGORIES]
    print(f"Top {TOP_N_CATEGORIES} categories by primary-tag count: "
          f"{[(c, len(by_category[c])) for c in top_categories]}")

    sample_rows = []
    for cat in top_categories:
        candidates = by_category[cat][:]
        rng.shuffle(candidates)
        chosen = candidates[:K_PER_CATEGORY]
        for h in chosen:
            sample_rows.append(
                {
                    "category": cat,
                    "title": h.get("title"),
                    "date": h.get("date"),
                    "lost": h.get("lost"),
                    "root_cause": h.get("root_cause"),
                    "code": h.get("vulnerable_code_snippet"),
                    "target": 1,
                }
            )

    print(f"Vulnerable sample: {len(sample_rows)} incidents across {len(top_categories)} categories")

    # benign baseline from final_dataset (dedup on id, keep unique safe-labeled samples)
    safe_by_id = {}
    with open(EVULLM_DIR / "final_dataset" / "train.jsonl") as f:
        for line in f:
            row = json.loads(line)
            if row["completion"] == "The label is safe." and row["id"] not in safe_by_id:
                safe_by_id[row["id"]] = row
    safe_rows = list(safe_by_id.values())
    rng.shuffle(safe_rows)
    n_benign = len(sample_rows)  # match count for a balanced overall FPR/recall comparison
    benign_sample = safe_rows[:n_benign]
    print(f"Benign baseline sample: {len(benign_sample)} (from {len(safe_rows)} unique safe examples available)")

    out_path = DATA_DIR / "pillar3_subsample.jsonl"
    with open(out_path, "w") as f:
        for row in sample_rows:
            f.write(json.dumps(row))
            f.write("\n")
        for row in benign_sample:
            # extract just the Solidity code from the instruction-formatted prompt
            prompt = row["prompt"]
            code = prompt.split("```Solidity")[-1].split("```")[0].strip() if "```Solidity" in prompt else prompt
            f.write(json.dumps({"category": "BENIGN_BASELINE", "code": code, "target": 0, "source_id": row["id"]}))
            f.write("\n")

    print(f"Saved {len(sample_rows) + len(benign_sample)} total rows to {out_path}")

    per_cat = defaultdict(int)
    for r in sample_rows:
        per_cat[r["category"]] += 1
    print("Per-category counts:", dict(per_cat))


if __name__ == "__main__":
    main()
