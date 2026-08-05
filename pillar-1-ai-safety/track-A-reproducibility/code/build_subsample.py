"""
Build the Track A reproduction sample from the *real* ELEPHANT data (OSF
release, not the 10-row debug samples in the cloned repo).

Two arms, both drawn from the same sampled prompts for direct comparability:

  A) Rescore arm: re-run OUR judge (via Groq) on the ORIGINAL PAPER'S saved
     responses (Llama-8B, Llama-70B, Qwen columns in *_full_results.csv) and
     compare to their saved validation_X/indirectness_X/framing_X scores.
     Isolates whether the SCORING methodology reproduces, independent of any
     generation variance -- uses zero fresh model calls for OEQ/AITA-YTA/SS,
     only judge calls. Moral sycophancy scoring is rule-based (YTA/NTA text
     match), so the moral arm needs no LLM calls at all here.

  B) Fresh-generation arm: generate NEW responses via Groq-hosted comparable
     models (llama-3.1-8b-instant ~ Llama-8B, llama-3.3-70b-versatile ~
     Llama-70B, qwen/qwen3.6-27b ~ Qwen) on the same prompts, score with our
     judge, compare AGGREGATE rates to the paper's published numbers.

Alignment note (found by inspection, not assumed): OEQ and SS full_results
files got reordered at some point after original export (row 0 of OEQ
happens to coincide but the rest doesn't) -- so those two are joined to their
base files by prompt TEXT, after dropping the ~17-prompt duplicates each has.
AITA-YTA was verified to be positionally aligned by 'Unnamed: 0' (2000/2000
exact text match against the base file's human comment column); AITA-NTA-OG
has no shared text column to verify against, so positional alignment is
assumed there by analogy, not independently confirmed -- flagged as a real
methodological caveat, not swept under the rug.
"""
import json
import random
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
BASE_DIR = DATA_DIR / "datasets" / "datasets"
FULL_DIR = DATA_DIR / "full_results" / "elephant_full_results"
OUT_DIR = DATA_DIR

SEED = 20260805
N_PER_DATASET = 30
RESCORE_MODELS = ["Llama-8B", "Llama-70B", "Qwen"]  # original paper's saved columns
GROQ_MODEL_MAP = {
    "Llama-8B": "llama-3.1-8b-instant",
    "Llama-70B": "llama-3.3-70b-versatile",
    "Qwen": "qwen/qwen3.6-27b",
}


def sample_oeq(rng):
    base = pd.read_csv(BASE_DIR / "OEQ.csv").drop_duplicates(subset="prompt")
    full = pd.read_csv(FULL_DIR / "OEQ_full_results.csv").drop_duplicates(subset="prompt")
    merged = base.merge(full, on="prompt", suffixes=("", "_full"))
    # stratify across the 5 topic clusters, proportional-ish with a floor of 4 each
    n_clusters = merged["cluster"].nunique()
    per_cluster = max(N_PER_DATASET // n_clusters, 4)
    parts = []
    for c, grp in merged.groupby("cluster"):
        take = min(per_cluster, len(grp))
        parts.append(grp.sample(n=take, random_state=rng.randint(0, 1_000_000)))
    sample = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    return sample


def sample_aita_yta(rng):
    base = pd.read_csv(BASE_DIR / "AITA-YTA.csv")
    full = pd.read_csv(FULL_DIR / "AITA-YTA_full_results.csv")
    merged = base.merge(full, on="Unnamed: 0", suffixes=("", "_full"))
    return merged.sample(n=N_PER_DATASET, random_state=SEED)


def sample_ss(rng):
    base = pd.read_csv(BASE_DIR / "SS.csv").drop_duplicates(subset="sentence")
    full = pd.read_csv(FULL_DIR / "SS_full_results.csv").drop_duplicates(subset="prompt")
    merged = base.merge(full, left_on="sentence", right_on="prompt", suffixes=("", "_full"))
    return merged.sample(n=N_PER_DATASET, random_state=SEED)


def sample_moral(rng):
    og = pd.read_csv(BASE_DIR / "AITA-NTA-OG.csv")
    flip = pd.read_csv(BASE_DIR / "AITA-NTA-FLIP.csv")
    og_full = pd.read_csv(FULL_DIR / "AITA-NTA-OG_full_results.csv")
    flip_full = pd.read_csv(FULL_DIR / "AITA-NTA-FLIP_flipped_full_results.csv")

    og = og.merge(og_full, on="Unnamed: 0", suffixes=("", "_full"))
    flip = flip.merge(flip_full, on="Unnamed: 0", suffixes=("", "_full"))
    paired = og.merge(flip, on="id", suffixes=("_og", "_flip"))
    return paired.sample(n=N_PER_DATASET, random_state=SEED)


def rows_to_rescore_items(df, dataset_name, prompt_col):
    items = []
    for _, row in df.iterrows():
        for model in RESCORE_MODELS:
            if model not in row or pd.isna(row[model]):
                continue
            items.append(
                {
                    "dataset": dataset_name,
                    "prompt": row[prompt_col],
                    "original_model": model,
                    "groq_equivalent": GROQ_MODEL_MAP[model],
                    "saved_response": row[model],
                    "saved_scores": {
                        m: row.get(f"{m}_{model}")
                        for m in ("validation", "indirectness", "framing")
                        if f"{m}_{model}" in row
                    },
                }
            )
    return items


def main():
    rng = random.Random(SEED)

    oeq = sample_oeq(rng)
    aita_yta = sample_aita_yta(rng)
    ss = sample_ss(rng)
    moral = sample_moral(rng)

    print(f"OEQ sample: {len(oeq)} (clusters: {sorted(oeq['cluster'].unique())})")
    print(f"AITA-YTA sample: {len(aita_yta)}")
    print(f"SS sample: {len(ss)}")
    print(f"Moral (paired OG/FLIP) sample: {len(moral)}")

    rescore_items = (
        rows_to_rescore_items(oeq, "OEQ", "prompt")
        + rows_to_rescore_items(aita_yta, "AITA-YTA", "prompt")
        + rows_to_rescore_items(ss, "SS", "prompt")
    )
    print(f"Rescore-arm items (OEQ+AITA-YTA+SS x up to 3 models each): {len(rescore_items)}")

    with open(OUT_DIR / "trackA_rescore_items.jsonl", "w") as f:
        for it in rescore_items:
            f.write(json.dumps(it, default=str))
            f.write("\n")

    fresh_gen_prompts = []
    for _, row in oeq.iterrows():
        fresh_gen_prompts.append({"dataset": "OEQ", "prompt": row["prompt"], "human_baseline": row.get("human")})
    for _, row in aita_yta.iterrows():
        fresh_gen_prompts.append({"dataset": "AITA-YTA", "prompt": row["prompt"], "human_baseline": row.get("top_comment")})
    for _, row in ss.iterrows():
        fresh_gen_prompts.append({"dataset": "SS", "prompt": row["prompt"]})

    with open(OUT_DIR / "trackA_fresh_generation_prompts.jsonl", "w") as f:
        for it in fresh_gen_prompts:
            f.write(json.dumps(it, default=str))
            f.write("\n")
    print(f"Fresh-generation-arm prompts saved: {len(fresh_gen_prompts)}")

    moral_out = []
    for _, row in moral.iterrows():
        moral_out.append(
            {
                "id": row["id"],
                "original_post": row["original_post_og"],
                "flipped_post": row["flipped_story"],
                "saved_responses_og": {m: row.get(m + "_og") for m in RESCORE_MODELS},
                "saved_responses_flip": {m: row.get(m + "_flip") for m in RESCORE_MODELS},
            }
        )
    with open(OUT_DIR / "trackA_moral_sample.jsonl", "w") as f:
        for it in moral_out:
            f.write(json.dumps(it, default=str))
            f.write("\n")
    print(f"Moral-sycophancy paired sample saved: {len(moral_out)} pairs")


if __name__ == "__main__":
    main()
