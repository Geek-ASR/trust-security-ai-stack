"""
Per-CWE-category, per-model accuracy / false-positive / false-negative
breakdown for the zero-shot vulnerability detection evaluation.

Uses Wilson score confidence intervals rather than the normal approximation
-- with n~15 per category, a normal-approximation CI can extend below 0% or
above 100%, which is meaningless. Wilson intervals stay valid at small n.

Also runs a chi-square test of independence (predicted-correct vs. category)
per model, to check whether accuracy differences across categories are
larger than what we'd expect from sampling noise alone, given n=15/category.

Ready to run as soon as results/zero_shot_predictions.jsonl is complete;
also runs fine on partial data to sanity-check formatting early.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd
from scipy import stats

RESULTS_DIR = Path(__file__).parent.parent / "results"
DATA_DIR = Path(__file__).parent.parent / "data"


def wilson_ci(successes, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load_results():
    recs = [json.loads(l) for l in open(RESULTS_DIR / "zero_shot_predictions.jsonl")]
    df = pd.DataFrame(recs)
    df = df[df["predicted"].notna()].copy()
    df["predicted"] = df["predicted"].astype(int)
    df["correct"] = (df["predicted"] == df["target"]).astype(int)
    return df


def per_category_model_table(df):
    rows = []
    for (model, cat), grp in df.groupby(["model", "cwe_category"]):
        vuln = grp[grp["target"] == 1]
        benign = grp[grp["target"] == 0]
        n = len(grp)
        acc = grp["correct"].mean()
        acc_lo, acc_hi = wilson_ci(grp["correct"].sum(), n)

        fnr = fnr_lo = fnr_hi = float("nan")
        if len(vuln):
            fn = (vuln["predicted"] == 0).sum()
            fnr = fn / len(vuln)
            fnr_lo, fnr_hi = wilson_ci(fn, len(vuln))

        fpr = fpr_lo = fpr_hi = float("nan")
        if len(benign):
            fp = (benign["predicted"] == 1).sum()
            fpr = fp / len(benign)
            fpr_lo, fpr_hi = wilson_ci(fp, len(benign))

        rows.append(
            {
                "model": model,
                "cwe_category": cat,
                "n": n,
                "n_vuln": len(vuln),
                "n_benign": len(benign),
                "accuracy": acc,
                "accuracy_ci": f"[{acc_lo:.0%}, {acc_hi:.0%}]",
                "false_negative_rate": fnr,
                "fnr_ci": f"[{fnr_lo:.0%}, {fnr_hi:.0%}]" if not math.isnan(fnr) else "n/a",
                "false_positive_rate": fpr,
                "fpr_ci": f"[{fpr_lo:.0%}, {fpr_hi:.0%}]" if not math.isnan(fpr) else "n/a",
            }
        )
    return pd.DataFrame(rows).sort_values(["model", "cwe_category"])


def chi_square_per_model(df):
    print("Chi-square test: is accuracy independent of CWE category? (per model)")
    print("(small/uneven cell counts at n=15/category -- treat as suggestive, not confirmatory)\n")
    for model, grp in df.groupby("model"):
        table = pd.crosstab(grp["cwe_category"], grp["correct"])
        if table.shape[0] < 2 or table.shape[1] < 2:
            print(f"  {model}: not enough variation to test")
            continue
        chi2, p, dof, _ = stats.chi2_contingency(table)
        sig = "significant at p<0.05" if p < 0.05 else "not significant"
        print(f"  {model}: chi2={chi2:.2f}, dof={dof}, p={p:.4f} ({sig})")
    print()


def worst_categories_overall(df):
    print("Categories with lowest mean accuracy across all 5 models (candidate 'hardest' categories):\n")
    summary = df.groupby("cwe_category")["correct"].agg(["mean", "count"]).sort_values("mean")
    print(summary.to_string(float_format=lambda x: f"{x:.1%}" if isinstance(x, float) else str(x)))
    print()


def fp_vs_fn_dominant_failure_mode(df):
    print("Dominant failure mode per category (aggregated across all models):\n")
    for cat, grp in df.groupby("cwe_category"):
        vuln = grp[grp["target"] == 1]
        benign = grp[grp["target"] == 0]
        fnr = (vuln["predicted"] == 0).mean() if len(vuln) else float("nan")
        fpr = (benign["predicted"] == 1).mean() if len(benign) else float("nan")
        dominant = "false-negative (misses real vulns)" if fnr > fpr else "false-positive (over-flags safe code)"
        print(f"  {cat}: FNR={fnr:.1%}, FPR={fpr:.1%} -> dominant failure: {dominant}")
    print()


def main():
    df = load_results()
    total_expected = 450 * 5
    print(f"Loaded {len(df)}/{total_expected} results with a real verdict "
          f"({len(df)/total_expected:.0%} complete)\n")

    table = per_category_model_table(df)
    out_path = RESULTS_DIR / "per_category_breakdown.csv"
    table.to_csv(out_path, index=False)
    print(f"Full per-model x per-category table saved to {out_path}\n")

    worst_categories_overall(df)
    fp_vs_fn_dominant_failure_mode(df)
    chi_square_per_model(df)


if __name__ == "__main__":
    main()
