"""
Moral sycophancy is rule-based (YTA/NTA text matching, not an LLM judge), so
this needs zero API calls -- runs immediately on the saved original-paper
responses in trackA_moral_sample.jsonl. Reuses the original authors'
compute_rates() logic verbatim (imported, not retyped).
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
ELEPHANT_DIR = Path(__file__).parent.parent / "elephant-original"
sys.path.insert(0, str(ELEPHANT_DIR))
from moral_sycophancy_scorer import compute_rates  # noqa: E402  (verbatim original logic)

RESCORE_MODELS = ["Llama-8B", "Llama-70B", "Qwen"]


def main():
    rows = [json.loads(l) for l in open(DATA_DIR / "trackA_moral_sample.jsonl")]
    print(f"Loaded {len(rows)} paired (original, flipped) posts\n")

    for model in RESCORE_MODELS:
        og_responses = [r["saved_responses_og"].get(model) for r in rows]
        flip_responses = [r["saved_responses_flip"].get(model) for r in rows]
        missing = sum(1 for a, b in zip(og_responses, flip_responses) if a is None or b is None)
        if missing:
            print(f"{model}: {missing}/{len(rows)} pairs missing a saved response, skipping those")
            og_responses = [a for a, b in zip(og_responses, flip_responses) if a is not None and b is not None]
            flip_responses = [b for a, b in zip(og_responses, flip_responses) if a is not None and b is not None]
        rates = compute_rates(og_responses, flip_responses)
        print(f"=== {model} (n={rates['counts']['denominator_pairs']}) ===")
        print(f"  moral sycophancy (both_NTA_rate): {rates['both_NTA_rate']:.1%}")
        print(f"  both_YTA_rate: {rates['both_YTA_rate']:.1%}")
        print(f"  consistent (NTA orig -> YTA flipped): {rates['side_A_NTA_side_B_YTA_rate']:.1%}")
        print(f"  consistent (YTA orig -> NTA flipped): {rates['side_A_YTA_side_B_NTA_rate']:.1%}")
        print(f"  refused/unparseable: {rates['refused']:.1%}")
        print()


if __name__ == "__main__":
    main()
