import json
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "primevul_full"


def load(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def cwe_list(r):
    cwe = r.get("cwe")
    if not cwe:
        return []
    if isinstance(cwe, str):
        return [cwe]
    return list(cwe)


def summarize(name, records):
    total = len(records)
    n_vuln = sum(1 for r in records if r["target"] == 1)
    n_benign = total - n_vuln
    cwe_counts = Counter()
    for r in records:
        cwe_counts.update(cwe_list(r))
    n_empty_cwe = sum(1 for r in records if not cwe_list(r))
    # among vulnerable only, since benign functions likely have no CWE
    vuln_records = [r for r in records if r["target"] == 1]
    vuln_empty_cwe = sum(1 for r in vuln_records if not cwe_list(r))
    multi_cwe = sum(1 for r in records if len(cwe_list(r)) > 1)

    print(f"=== {name} ===")
    print(f"total: {total}, vulnerable: {n_vuln}, benign: {n_benign}")
    print(f"records with empty cwe field: {n_empty_cwe} ({n_empty_cwe/total:.1%})")
    print(f"vulnerable records with empty cwe: {vuln_empty_cwe} / {n_vuln}")
    print(f"records with more than one cwe tag: {multi_cwe}")
    print(f"distinct non-empty CWE values: {len(cwe_counts)}")
    print("top 20 CWE categories by count:")
    for cwe, count in cwe_counts.most_common(20):
        print(f"  {cwe!r}: {count}")
    print()


if __name__ == "__main__":
    test = load(DATA_DIR / "primevul_test.jsonl")
    test_paired = load(DATA_DIR / "primevul_test_paired.jsonl")
    summarize("primevul_test.jsonl", test)
    summarize("primevul_test_paired.jsonl", test_paired)

    # peek at a paired example structure to see how pairing is represented
    print("=== sample paired record keys ===")
    print(json.dumps(test_paired[0], indent=2)[:1500])
