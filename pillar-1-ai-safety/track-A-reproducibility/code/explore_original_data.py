"""
Free exploratory analysis of the FULL original ELEPHANT data (all ~3000-3800
rows per dataset, all 11 models, not just our 90-row subsample) -- zero API
calls, since we're just re-deriving descriptive stats from the authors' own
published per-example scores. Useful for motivating both Track A (does our
subsample's topic-cluster mix look representative?) and Track B (which
models already look most/least sycophantic in the original data, and does
scale within a model family predict less sycophancy -- context for whether
reasoning might plausibly do the same).
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data" / "full_results" / "elephant_full_results"

MODELS = ["Human", "GPT-5", "GPT-4o", "Claude", "Gemini", "DeepSeek", "Qwen",
          "Llama-70B", "Llama-17B", "Llama-8B", "Mistral-24B", "Mistral-7B"]
METRICS = ["validation", "indirectness", "framing"]


def model_rates(df, dataset_name):
    print(f"=== {dataset_name}: mean rate per model per metric ===")
    rows = []
    for model in MODELS:
        row = {"model": model}
        for metric in METRICS:
            col = f"{metric}_{model}"
            if col in df.columns:
                row[metric] = pd.to_numeric(df[col], errors="coerce").mean()
        if len(row) > 1:
            rows.append(row)
    out = pd.DataFrame(rows).set_index("model")
    print(out.round(3).to_string())
    print()
    return out


def cluster_breakdown(oeq_df):
    print("=== OEQ: sycophancy rate by topic cluster (Llama-70B, as a representative open model) ===")
    for cluster, grp in oeq_df.groupby("cluster"):
        rates = {m: pd.to_numeric(grp[f"{m}_Llama-70B"], errors="coerce").mean()
                 for m in METRICS if f"{m}_Llama-70B" in grp.columns}
        print(f"  cluster {cluster} (n={len(grp)}): {rates}")
    print()


def scale_within_family(all_rates):
    print("=== Does scale within a family predict lower sycophancy? (context for Track B) ===")
    pairs = [("Llama-8B", "Llama-70B"), ("Mistral-7B", "Mistral-24B")]
    for small, big in pairs:
        if small not in all_rates.index or big not in all_rates.index:
            continue
        for metric in METRICS:
            if metric not in all_rates.columns:
                continue
            s, b = all_rates.loc[small, metric], all_rates.loc[big, metric]
            direction = "bigger is LESS sycophantic" if b < s else "bigger is MORE sycophantic"
            print(f"  {metric}: {small}={s:.3f} vs {big}={b:.3f} -> {direction} ({abs(b-s):.3f} diff)")
    print()


def main():
    oeq = pd.read_csv(DATA_DIR / "OEQ_full_results.csv")
    aita = pd.read_csv(DATA_DIR / "AITA-YTA_full_results.csv")
    ss = pd.read_csv(DATA_DIR / "SS_full_results.csv")

    oeq_rates = model_rates(oeq, "OEQ")
    aita_rates = model_rates(aita, "AITA-YTA")
    ss_rates = model_rates(ss, "SS")

    cluster_breakdown(oeq)

    # average across the 3 datasets for an overall ranking
    combined = pd.concat([oeq_rates, aita_rates, ss_rates]).groupby(level=0).mean()
    print("=== Overall ranking (mean across OEQ/AITA-YTA/SS): most -> least sycophantic on 'validation' ===")
    print(combined.sort_values("validation", ascending=False).round(3).to_string())
    print()

    scale_within_family(combined)


if __name__ == "__main__":
    main()
