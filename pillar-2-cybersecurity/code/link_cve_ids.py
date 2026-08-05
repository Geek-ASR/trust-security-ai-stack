"""
Recover each sampled vulnerable record's CVE ID by joining against the BigVul
dataset (bstee615/bigvul on Hugging Face) on (project, commit_id) -- more
robust than trying to replicate PrimeVul's internal big_vul_idx positional
indexing, which doesn't line up with this mirror's row ordering.
"""
import json
from pathlib import Path

from datasets import load_dataset

DATA_DIR = Path(__file__).parent.parent / "data"


def load_jsonl(path):
    recs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def main():
    subsample = load_jsonl(DATA_DIR / "pillar2_subsample.jsonl")
    print(f"Loaded {len(subsample)} subsample rows")

    ds = load_dataset("bstee615/bigvul")
    lookup = {}
    dupe_conflicts = 0
    for split in ds.values():
        for row in split:
            key = (row["project"], row["commit_id"])
            if key in lookup and lookup[key]["CVE ID"] != row["CVE ID"]:
                dupe_conflicts += 1
            lookup[key] = row
    print(f"Built lookup with {len(lookup)} unique (project, commit_id) keys")
    print(f"Conflicting CVE IDs for same key seen: {dupe_conflicts}")

    matched = 0
    enriched = []
    for row in subsample:
        key = (row["vuln_project"], row["vuln_commit_id"])
        bv = lookup.get(key)
        entry = dict(row)
        if bv is not None:
            matched += 1
            entry["bigvul_cve_id"] = bv["CVE ID"]
            entry["bigvul_cwe_id"] = bv["CWE ID"]
            entry["bigvul_cve_page"] = bv["CVE Page"]
        else:
            entry["bigvul_cve_id"] = None
            entry["bigvul_cwe_id"] = None
            entry["bigvul_cve_page"] = None
        enriched.append(entry)

    print(f"Matched CVE info for {matched}/{len(subsample)} sampled records")

    n_agree = sum(
        1
        for e in enriched
        if e["bigvul_cwe_id"] and e["bigvul_cwe_id"] == e["cwe_category"]
    )
    n_have_both = sum(1 for e in enriched if e["bigvul_cwe_id"])
    print(f"Of matched records, PrimeVul tag == BigVul tag: {n_agree}/{n_have_both}")

    out_path = DATA_DIR / "pillar2_subsample_with_cve.jsonl"
    with open(out_path, "w") as f:
        for e in enriched:
            f.write(json.dumps(e, default=str))
            f.write("\n")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
