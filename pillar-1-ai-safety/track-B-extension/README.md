# Track B: Does explicit reasoning reduce social sycophancy?

**Target venue:** NeurIPS 2026 workshop (LLM evaluation / trustworthy AI theme). Paper deadline ~Aug 29, 2026; notification ~Sept 29, 2026. Exact workshop TBD once draft is further along — candidates found so far include workshops under the "Interpretability for Discovery" and "LLM-eval@NeurIPS" umbrellas (Dec 2026 dates); needs a final check of the specific CFP once we're ready to submit.

## Proposed research question

The original ELEPHANT paper (arXiv:2505.13995) tested 11 models from the 2024-early 2025 generation, none of which were dedicated "reasoning"/extended-thinking models. Reasoning models are explicitly trained to deliberate before answering, which plausibly could reduce sycophantic pattern-matching to what the user wants to hear — but this hasn't been rigorously tested with ELEPHANT's specific validated metrics.

**Question:** Does turning on explicit reasoning/extended thinking (holding the base model constant) reduce measured social sycophancy, using ELEPHANT's own validation/indirectness/framing/moral metrics?

**Why this design is clean:** comparing the *same* model with reasoning on vs. off is a controlled comparison — it isolates the effect of deliberation from confounds like model scale or training data that would contaminate a simple "test more/newer models" comparison.

### Redundancy re-check (done a second time, since this is a fast-moving area)

Two pieces of existing evidence found, neither of which closes this gap — but both sharpen the framing:

1. **The same non-peer-reviewed BlueDot fellowship blog post** already cited for the CWE-style data-quality critique (Alexis Wang, "Measuring Moral Sycophancy Is Harder Than It Looks," Jan 2026 Technical AI Safety Project Sprint) also ran a quick DeepSeek R1 vs. V3 comparison and found R1 (reasoning) scored lower moral sycophancy (0.49 vs. 0.66). This is suggestive, not a real answer: **one metric** (moral only, not validation/indirectness/framing), **one model pair**, not peer-reviewed, not systematic.
2. **A real, separate peer-reviewed-track paper** (arXiv:2601.18334, "Overalignment in Frontier LLMs: An Empirical Study of Sycophantic Behaviour in Healthcare") found the opposite kind of result in a different setting: Qwen3.5-27B's reasoning trace frequently *rationalizes* sycophantic agreement under "expert nudge" (authority-based pressure) in healthcare scenarios — reasoning facilitating rather than reducing sycophancy. Different benchmark (healthcare authority-pressure, not ELEPHANT's social-face-preservation framing), different mechanism, but directly relevant counter-evidence to cite.

**Net effect on the pitch:** this is not a "confirm the obvious" study — existing signal is genuinely mixed (one exploratory check says reasoning helps on one metric; an adjacent real paper says reasoning can backfire in a different sycophancy context). A rigorous, multi-metric, multi-architecture, peer-reviewed test on ELEPHANT specifically remains open, and the mixed prior evidence makes the outcome genuinely uncertain rather than a foregone conclusion — a stronger pitch than what we had before this check.

### Free motivating analysis on the original data itself (zero API calls, real finding)

Ran `code/explore_original_data.py` on the full original ELEPHANT results (thousands of rows, not our subsample) to see if the *existing* 11-model data already hints at anything relevant before we spend any Groq budget. Two real, useful findings:

1. **Scale alone doesn't uniformly reduce sycophancy — and where it fails is telling.** Within both the Llama (8B→70B) and Mistral (7B→24B) families, going bigger *reduces* validation and indirectness sycophancy, but *increases* framing sycophancy (Mistral: 0.642→0.909, a 27-point jump the wrong way). Framing sycophancy is specifically about whether the model challenges the user's underlying premise rather than working within it — arguably the dimension most plausibly helped by deliberate multi-step reasoning rather than scale/pattern-matching alone. This sharpens Track B's hypothesis: **if scale reliably fixed framing sycophancy, reasoning wouldn't need to be the lever — but it doesn't, which is exactly the gap reasoning-as-deliberation could plausibly fill.** Worth stating explicitly as motivation in the writeup, not just an aside.
2. **GPT-5 already shows notably lower validation sycophancy than GPT-4o in the original data** (0.606 vs. 0.815, averaged across OEQ/AITA-YTA/SS) but is *not* lower on framing (0.883, among the highest) — consistent with point 1: whatever's driving GPT-5's improvement (possibly reasoning-adjacent training) isn't closing the framing gap either. Same pattern, independent evidence.
3. Minor methodological validation, not a finding: OEQ's sycophancy rate varies hugely by topic cluster (Llama-70B validation: 0.50 in cluster 2 vs. 0.95 in cluster 0) — confirms Track A's decision to stratify the sample across clusters rather than sample randomly was the right call, not a formality.

## Planned method — zero-cost design (Groq free tier, no local compute needed)

No budget for paid APIs, so both reasoning-toggle model families run via **Groq's free tier** (console.groq.com, no credit card, shared with Track A):

1. **`openai/gpt-oss-20b` (and/or `gpt-oss-120b`) on Groq** — OpenAI's open-weight reasoning model, which natively supports a `reasoning_effort` parameter (low/medium/high). Compare low vs. high reasoning effort, same model weights, same prompts.
2. **Qwen3 on Groq** — natively supports `enable_thinking` true/false (or `/think` `/no_think`) within the same model. Compare thinking-on vs. thinking-off.

Running **two independent reasoning-toggle architectures** rather than one is a deliberate strengthening: if both show the same directional effect, that's a much more general, publishable claim than a single-model curiosity. If they disagree, that's an interesting finding in itself.

3. Run the same subsampled datasets from Track A through both modes of each model.
4. Score with the same adapted-for-Groq ELEPHANT scorers used in Track A — same judge, same metrics, so results are directly comparable to both the original paper and to Track A's reproduction numbers.
5. Analyze: does reasoning mode systematically shift any of the 4 metrics? Does the effect differ by dimension (e.g., maybe reasoning reduces "answer sycophancy" but not "validation sycophancy," which is more about emotional tone than factual correctness)?
6. Optional secondary angle: incorporate the Track A data-quality spot-check (BlueDot audit finding) as a robustness control on the AITA-NTA-FLIP comparisons.

## Status

- [x] Confirmed zero-cost design using Groq free tier, shared pipeline with Track A.
- [x] User created free Groq API key (shared across all pillars, `Research work/.env`).
- [x] Confirmed `reasoning_effort` (gpt-oss, low/medium/high) and `reasoning_effort: "none"`/`"default"` (Qwen3.6-27B) are live and working on Groq's API right now — verified directly while fixing a bug in Pillar 2's evaluation script, which hit the exact same models defaulting to hidden "thinking" mode and burning their token budget on reasoning traces before answering. Confirms the reasoning toggle is real and controllable, not just documented.
- [x] Redundancy re-checked a second time (see above) — angle remains open.
- [x] Track A's `build_subsample.py` now produces real 90-prompt + 30-pair samples from the actual OSF data (not the repo's 10-row debug samples) — Track B will reuse the same `trackA_fresh_generation_prompts.jsonl` prompts so results are directly comparable to Track A's Arm B baseline (reasoning off = same models as Track A's fresh-generation arm).
- [ ] Everything execution-related is pending Track A's Arm A/B calls and Pillar 2's evaluation run both clearing — same Groq models, same daily token budgets, deliberately sequenced rather than run concurrently.

## Fallback scope if reasoning-toggle parameters aren't exposed by Groq

Simplify to: re-run ELEPHANT metrics on a handful of models released after the original study's cutoff (still via Groq free tier), reporting whether field-wide sycophancy rates have shifted — still a legitimate, timely contribution, just less mechanistically interesting than the reasoning-toggle design.
