"""
Compare PrimeVul's CWE tag against NVD's current authoritative CWE
assignment for each sampled record, to get an independent validity check
on the label quality underpinning our per-category breakdown.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def main():
    subsample = [json.loads(l) for l in open(DATA_DIR / "pillar2_subsample_with_cve.jsonl")]
    nvd = json.loads((DATA_DIR / "nvd_cwe_lookup.json").read_text())

    rows = []
    for r in subsample:
        cve = r.get("bigvul_cve_id")
        if not cve:
            continue
        nvd_entry = nvd.get(cve, {})
        if nvd_entry.get("status") != "ok":
            rows.append({**r, "nvd_status": nvd_entry.get("status", "missing"), "nvd_cwes": []})
            continue
        nvd_cwes = [c["value"] for c in nvd_entry.get("cwes", [])]
        rows.append({**r, "nvd_status": "ok", "nvd_cwes": nvd_cwes})

    n_total = len(rows)
    n_nvd_ok = sum(1 for r in rows if r["nvd_status"] == "ok")
    n_nvd_has_cwe = sum(1 for r in rows if r["nvd_status"] == "ok" and r["nvd_cwes"])
    n_agree = sum(
        1 for r in rows
        if r["nvd_status"] == "ok" and r["cwe_category"] in r["nvd_cwes"]
    )
    n_disagree = sum(
        1 for r in rows
        if r["nvd_status"] == "ok" and r["nvd_cwes"] and r["cwe_category"] not in r["nvd_cwes"]
    )

    print(f"Sampled records with a CVE ID: {n_total}")
    print(f"NVD lookup succeeded: {n_nvd_ok}")
    print(f"NVD record has at least one CWE assigned: {n_nvd_has_cwe}")
    print(f"PrimeVul tag matches NVD's assignment: {n_agree}/{n_nvd_has_cwe} ({n_agree/n_nvd_has_cwe:.1%})")
    print(f"PrimeVul tag disagrees with NVD's assignment: {n_disagree}/{n_nvd_has_cwe} ({n_disagree/n_nvd_has_cwe:.1%})")

    # per-category agreement
    per_cat = defaultdict(lambda: {"agree": 0, "disagree": 0, "no_nvd_cwe": 0})
    for r in rows:
        if r["nvd_status"] != "ok":
            continue
        cat = r["cwe_category"]
        if not r["nvd_cwes"]:
            per_cat[cat]["no_nvd_cwe"] += 1
        elif cat in r["nvd_cwes"]:
            per_cat[cat]["agree"] += 1
        else:
            per_cat[cat]["disagree"] += 1

    print("\nPer-category agreement (PrimeVul tag vs NVD):")
    for cat, d in sorted(per_cat.items(), key=lambda x: -(x[1]["agree"] + x[1]["disagree"])):
        total_checked = d["agree"] + d["disagree"]
        rate = d["agree"] / total_checked if total_checked else float("nan")
        print(f"  {cat}: agree={d['agree']} disagree={d['disagree']} no_nvd_cwe={d['no_nvd_cwe']} (agreement rate: {rate:.0%})" if total_checked else f"  {cat}: no comparable NVD data")

    # show disagreement examples
    print("\nDisagreement examples (PrimeVul tag -> NVD's actual assignment):")
    shown = 0
    for r in rows:
        if r["nvd_status"] == "ok" and r["nvd_cwes"] and r["cwe_category"] not in r["nvd_cwes"]:
            print(f"  {r['bigvul_cve_id']}: PrimeVul says {r['cwe_category']}, NVD says {r['nvd_cwes']}")
            shown += 1
            if shown >= 15:
                break

    out_path = DATA_DIR / "pillar2_cwe_validation.jsonl"
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str))
            f.write("\n")
    print(f"\nSaved full validation table to {out_path}")


if __name__ == "__main__":
    main()
