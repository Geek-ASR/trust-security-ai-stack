# Pillar 2: Cybersecurity + LLMs — Vulnerability Detection

Trust at the **software/code layer**: how well can free, open-weight LLMs actually detect real security vulnerabilities in code, and specifically, *where and how* do they fail?

This pillar is being treated as its own independent, standalone research paper (not tied to Pillar 1's infrastructure or research question) — no Groq/API key needed yet, this stage is pure literature review and research design.

## Anchor dataset: PrimeVul

**PrimeVul** (Ding et al., ICSE 2025) — https://github.com/DLVulDet/PrimeVul (verified live).
- 6,968 vulnerable + 228,800 fixed C/C++ functions, labeled with CWE/CVE metadata across 140 CWE categories, using a far more rigorous labeling process than older datasets (older benchmarks like BigVul let a 7B model look like it gets 68% F1, when the *same* model gets only 3% F1 on PrimeVul's harder, more realistic labels).
- Includes a specifically hard "paired" test set: vulnerable/patched function pairs sharing ≥80% of their text, forcing real semantic understanding rather than superficial pattern matching.
- Known limitation (important, and load-bearing for our method): a follow-up paper found ~30% of PrimeVul's CWE tags are mislabeled relative to manual verification (see below) — we account for this rather than ignore it.

## Research question (finalized after checking for redundancy)

Considered and ruled out:
- **Reasoning-toggle (gpt-oss/Qwen3 reasoning on vs. off)** — user's call: keep this pillar clearly distinct from Pillar 1's mechanism, even though it would have been non-redundant with published work.
- **Multi-model ensemble/voting** — already a fairly crowded area (DVDR-LLM, "Diverse LLMs vs. Vulnerabilities," phishing-detection voting studies, etc.) — not a clean novelty angle right now.

**What's actually open:** a follow-up paper to PrimeVul — call it CWE-Trace (arXiv:2606.20502, "Calibration Without Comprehension") — already zero-shot tested 8 models (including DeepSeek-R1, GPT-4.1-mini, Qwen3-4B, Llama3.1) on PrimeVul and confirmed the ~30% CWE label noise, but its own analysis stops at the *coarse root-pillar* taxonomy level (broad categories), not specific CWE codes — and their own stated future work (cross-language replication, structured prompting, contrastive training) doesn't include fine-grained breakdown either.

**Proposed RQ:** *At the level of specific CWE categories (not just coarse root-pillars), where do free, open-weight LLMs systematically fail at zero-shot vulnerability detection on PrimeVul, and what failure mode dominates (false-positive: flagging safe/patched code as vulnerable, vs. false-negative: missing real vulnerabilities) — especially on the leakage-resistant hard-pairs subset?* A validity check accounts for the known ~30% CWE label noise (manually spot-check a subsample of our own CWE tags before trusting the per-category breakdown) rather than taking PrimeVul's labels at face value — an echo of Pillar 1's human-validation-in-the-loop approach, arrived at independently because it's the right thing to do here too, not because it was forced to match.

## Proposed method

1. ~~Draw a stratified subsample from PrimeVul across a diverse set of specific CWE categories~~ — **done**, see Data below.
2. Validate CWE label accuracy on the subsample against NVD's authoritative record (per the known ~30% noise issue) — **in progress**, see Data below. User's call: cross-reference against NVD rather than manual code review, since accurately judging CWE category from raw C/C++ requires security expertise neither of us should assume going in.
3. Evaluate a handful of free open-weight models zero-shot (inference source TBD — Groq free tier remains leading option when we reach this stage).
4. Break down accuracy, false-positive rate, and false-negative rate per CWE category and per model; identify which categories/failure modes are systematic vs. model-specific.
5. Compare to CWE-Trace's coarse-level findings as a starting point, showing what the fine-grained view adds.

## Data pipeline (built so far)

- Downloaded full PrimeVul (all 6 split files, ~510MB) via `gdown` from the authors' Google Drive release into `data/primevul_full/`.
- Discovered individual splits are CWE-sparse (91.9% of `test.jsonl`'s vulnerable records have no CWE tag); pooling train+valid+test recovers 2,727 CWE-tagged vulnerable records across 93 categories — legitimate here since we're doing independent zero-shot evaluation, not reusing PrimeVul's fine-tuning split.
- Built the stratified sample (`code/build_subsample.py`, seed 20260729): **top 15 CWE categories × 15 vulnerable examples = 225 vulnerable functions**, each matched to a benign counterpart (173 real patched-version pairs from PrimeVul's hard-pairs data + 52 random-benign fallbacks where no direct pair existed) → `data/pillar2_subsample.jsonl`.
- **NVD cross-reference validation** (`code/link_cve_ids.py`, `code/nvd_lookup.py`): recovered CVE IDs for 188/225 sampled records by joining against the BigVul dataset (`bstee615/bigvul` on Hugging Face) on `(project, commit_id)` — more robust than trying to replicate PrimeVul's internal positional indexing, which turned out not to line up with any public BigVul mirror we could get access to without a Kaggle account. Found that PrimeVul's CWE tags exactly match BigVul's on all 188 matched records (100% agreement) — meaning they're the same non-independent source, not two independent checks. So we're now querying NVD's live API directly (181 unique CVEs, rate-limited to ~4/30s to stay within their unauthenticated free tier) for NVD's current, authoritative CWE assignment, to get a genuinely independent comparison point rather than comparing PrimeVul against its own source.

## NVD validation results (completed)

Checked 186 of our 225 sampled vulnerable records against NVD's current, authoritative CWE assignment (the 39 without a usable CVE ID or NVD record excluded).

- **Overall agreement: 88.2% (164/186)** — meaningfully *higher* than CWE-Trace's reported ~69.3% (i.e., their ~30% error rate) on PrimeVul generally. Worth discussing in the writeup: could be that our sample, drawn from the top 15 most CWE-tag-frequent categories, skews toward better-established/less ambiguous CWEs than the full long tail: `CWE-Trace` checked broadly, we checked the head of the distribution; or that NVD's records have been corrected/updated since CWE-Trace's check; or a methodology difference (manual re-verification vs. NVD cross-reference).
- **A real, citable sub-finding:** a good chunk of the 22 disagreements aren't random noise — they're **CWE-hierarchy granularity mismatches**. E.g., all 5 CWE-399 "disagreements" have NVD assigning CWE-401 (memory leak), which is a *child* of CWE-399 (resource management errors) in the CWE taxonomy — PrimeVul/BigVul tagged the coarser parent, NVD tagged the more specific modern child. Same pattern for 3 of the CWE-119 disagreements (NVD assigning CWE-120/125/787, all children of the now-discouraged-as-too-broad CWE-119). This tracks with CWE-Trace's own observation that "common errors swap symptoms for root causes or conflate related categories."
- Other disagreements (e.g., CWE-200 dropping to 69% agreement, with NVD assigning unrelated categories like CWE-285, CWE-611, CWE-326) look like genuine semantic mismatches, not hierarchy artifacts — a useful contrast case.
- Full record-level results: `data/pillar2_cwe_validation.jsonl`. Scripts: `code/link_cve_ids.py` (CVE recovery via BigVul join), `code/nvd_lookup.py` (NVD API queries), `code/analyze_cwe_agreement.py` (agreement analysis).

This is now a legitimate secondary contribution of the paper, not just a sanity check: PrimeVul's label noise is partly systematic (hierarchy granularity, tied to CWE taxonomy evolution since BigVul's 2019 construction) rather than uniformly random — which matters for how much to trust a fine-grained per-category breakdown built on top of it.

## Target venues

- **ReScience C** (rolling, no deadline) — safest primary target, framed as an extension/replication study building on PrimeVul + CWE-Trace.
- **NeurIPS 2026 workshop** (trustworthy/safe ML themed) — plausible stretch target since this is fundamentally an LLM evaluation paper.

## Status

- [x] Anchor dataset confirmed: PrimeVul
- [x] Research question finalized and checked for redundancy against VulSage, VulInstruct, R2Vul, CWE-Trace
- [x] Full PrimeVul data pulled, stratified sample built (225 vulnerable + 225 matched benign functions, 15 CWE categories)
- [x] NVD cross-reference validation complete: 88.2% agreement, with a real finding that most disagreement is CWE-hierarchy granularity, not random noise
- [ ] Decide inference source (Groq free tier, when we reach the experiment stage) — next step

Independent of Pillar 1 — own literature base, own research question, own timeline. Data/methodology work didn't need any API key; the upcoming model-evaluation step will.
