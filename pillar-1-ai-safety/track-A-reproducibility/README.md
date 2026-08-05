# Track A: Reproducing ELEPHANT (social sycophancy benchmark)

**Target venue:** ReScience C (https://rescience.github.io/) — platinum open-access, peer-reviewed via open GitHub review, no fixed deadline.

## Original paper

Cheng et al. 2025, "ELEPHANT: Measuring and Understanding Social Sycophancy in LLMs," arXiv:2505.13995.
Official code: `elephant-original/` (cloned from https://github.com/myracheng/elephant).

## What the original paper did

- **7 sycophancy dimensions:** validation, indirectness, framing (measured against a human baseline via Eq. 1: mean(model_score - human_score) per example), moral (Eq. 3: rate of affirming both sides of a flipped moral conflict), plus feedback/answer/mimicry sycophancy from prior work.
- **4 datasets** (all derived from public Reddit data + advice columns): OEQ (3,027), AITA-YTA (2,000), SS (3,777), AITA-NTA-FLIP (1,591 paired).
- **11 models tested**, spanning OpenAI, Anthropic, Google, Meta Llama, Mistral, DeepSeek, Qwen.
- **Scoring:** GPT-4o binary classifier judge for validation/indirectness/framing; moral sycophancy is rule-based YTA/NTA text matching on responses generated under a *separate, constrained* prompt ("...Output only YTA or NTA").
- Human baseline scores precomputed and included in their released data.

## Real OSF data pulled (not just the repo's 10-row debug samples)

The GitHub repo only ships 10-example samples. The real data lives on OSF (`osf.io/r3dmj`, view-only token in the repo README) and was pulled via the OSF public API (folder listing needs the `view_only` query param or it 401s):

- `data/datasets/datasets/*.csv` — the 4 real prompt sets, row counts verified to match the paper exactly (OEQ 3027, AITA-YTA 2000, SS 3777, AITA-NTA-FLIP 1591).
- `data/full_results/elephant_full_results/*.csv` — a major find: the **original paper's actual saved responses and computed scores for all 11 models**, not just published aggregate table numbers. This includes free open-weight models (Llama-8B, Llama-70B, Qwen, Mistral-7B/24B, DeepSeek) alongside proprietary ones.

This changes Track A's design for the better — see below.

## Reproduction design: two arms

**Arm A — Rescore (judge-only reproduction).** Re-run OUR Groq-based judge on the ORIGINAL PAPER'S saved responses (Llama-8B/70B, Qwen columns) and compare to their saved `validation_X`/`indirectness_X`/`framing_X` scores. Isolates whether the *scoring methodology* reproduces, independent of any generation variance. Needs judge calls only, no fresh model generation, for OEQ/AITA-YTA/SS.

**Arm B — Fresh generation.** Generate NEW responses via Groq-hosted comparable models (`llama-3.1-8b-instant` ~ Llama-8B, `llama-3.3-70b-versatile` ~ Llama-70B, `qwen/qwen3.6-27b` ~ Qwen) on the same sampled prompts, score with our judge, compare aggregate rates to the paper's published numbers. This is the classic reproduction design, and the only viable path for moral sycophancy (see caveat below).

Both arms draw from the **same 90 sampled prompts** (30 each from OEQ/AITA-YTA/SS, stratified across OEQ's 5 topic clusters) **+ 30 paired posts** for moral sycophancy, built by `code/build_subsample.py`.

**Alignment caveat (found by inspection, disclosed rather than assumed away):** the OSF `full_results` files aren't all in the same row order as the base dataset files. OEQ and SS were joined to their base files by prompt *text* (after dropping ~17 duplicate-prompt rows each has) because positional order didn't match. AITA-YTA was verified positionally aligned by cross-checking 2000/2000 exact text matches against the base file's human-comment column. AITA-NTA-OG has no shared text field to verify against, so positional alignment there is assumed by analogy to AITA-YTA's confirmed pattern — not independently confirmed. Worth an extra check before the final write-up.

## Real finding already made (no API calls needed): moral sycophancy can't reuse the saved rescore-arm data

Tried scoring Arm A for moral sycophancy first, since it's rule-based (YTA/NTA text match) and needs zero LLM calls — ran immediately via `code/score_moral_rescore_arm.py`. Result: ~90-100% "unparseable" for Llama-8B and Qwen. Root cause, confirmed by inspection: the saved Llama-8B/Qwen responses in `AITA-NTA-OG_full_results.csv` are full free-text advice ("You are not the asshole in this situation...") — they were generated for the framing/validation/indirectness analysis on this dataset, not under the original paper's *separate*, constrained "Output only YTA or NTA" prompt that moral sycophancy scoring actually requires. Regex-scanning the free text for stray "YTA"/"NTA" substrings would just introduce false positives/negatives, not fix this.

**Conclusion:** Arm A (rescore) works for validation/indirectness/framing on OEQ/AITA-YTA/SS, but **moral sycophancy needs Arm B (fresh generation) with the original constrained prompt** — no shortcut available here. Documented as a real scope boundary, not a bug to keep chasing.

## Prep code written (ready to run, execution deferred)

- `code/build_subsample.py` — **run, working.** Builds the stratified sample + both arms' input files (`data/trackA_rescore_items.jsonl`, `data/trackA_fresh_generation_prompts.jsonl`, `data/trackA_moral_sample.jsonl`).
- `code/groq_scorer.py` — **written, import-verified, not yet executed.** Judge scorer pointed at Groq, reusing the original authors' exact prompt text verbatim (imported directly from `elephant-original/sycophancy_scorers.py`, not retyped, for fidelity). Judge model: `llama-3.3-70b-versatile`, deliberately kept off gpt-oss/Qwen so it doesn't compete with Track B's reasoning-toggle experiments for the same daily token budgets.
- `code/score_moral_rescore_arm.py` — **run, working, zero API cost.** Rule-based YTA/NTA rate comparison, reuses the original authors' `compute_rates()` verbatim.

**Deliberately not yet executed:** anything requiring fresh Groq generation calls (Arm B, and Arm A's judge calls) — held until Pillar 2's evaluation run clears its daily token budgets, since several of the same Groq models are shared across pillars.

## Steps

1. [x] Confirm zero-cost design (Groq free tier).
2. [x] User created a free Groq API key, shared across all pillars (`Research work/.env`).
3. [x] Pull full datasets from OSF — done via OSF public API, not just the repo's 10-row samples.
4. [x] Draw stratified subsample (30/dataset + 30 moral pairs) — `build_subsample.py`.
5. [x] Adapt scorer code to call Groq's endpoint — `groq_scorer.py`, import-verified.
6. [x] Run the zero-cost part of the pipeline (moral rescore arm) — real result: doesn't work with this data source, documented above.
7. [ ] Run Arm A (rescore) judge calls on OEQ/AITA-YTA/SS once Groq budget is free.
8. [ ] Run Arm B (fresh generation) on OEQ/AITA-YTA/SS + moral sycophancy with the constrained prompt.
9. [ ] User hand-labels a small validation sample; compute judge agreement (κ) against our Groq judge.
10. [ ] Compare our rates to the paper's published Table results AND to Arm A's saved-response comparison; document matches/deviations.
11. [ ] Manual spot-check of AITA-NTA-FLIP for perspective-flip data quality (BlueDot audit's known issue); report impact.
12. [ ] Write up as a ReScience C article in `draft/`.
13. [ ] Submit: public git repo + article.

## Notes / risks

- Substituting the judge model is a real deviation from the original methodology — reported transparently, validated via the human-labeling step (still pending).
- ReScience C accepts partial/failed reproductions too, as long as they're honestly reported.
- No cost anywhere in this pipeline — Groq's free tier needs no credit card.
