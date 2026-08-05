# Pillar 3: Blockchain + Distributed Systems + AI — Smart Contract Security

Trust at the **decentralized infrastructure layer**: can free, open-weight LLMs reliably flag smart contract vulnerabilities that caused real, historically-documented financial losses — and where specifically do they fail?

## Anchor dataset: EVuLLM (cloned, inspected)

**EVuLLM** — https://github.com/Datalab-AUTH/EVuLLM-dataset (verified live, cloned to `evullm-original/`). Paper: "EVuLLM: Ethereum Smart Contract Vulnerability Detection Using Large Language Models" (MDPI Electronics, 2025).

The repo turned out to contain **two genuinely different datasets**, worth separating clearly:

1. **`final_dataset/{train,val,test}` — a fine-tuning dataset.** 462 unique code samples (231 vulnerable + 231 safe, perfectly balanced), each paraphrased 5x for instruction-tuning diversity (2,310 total rows in train alone). The "safe" half comes from real audited contracts in the well-known GPTScan-Top200 benchmark (confirmed by reading `top200.py`, which extracts and samples functions from that corpus); the "vulnerable" half comes from #2 below. This is what the EVuLLM paper's own contribution (QLoRA-fine-tuning small models like Llama-2-7b, GPT-2-XL) was built on — **not** what we want to reuse directly, since our angle is zero-shot evaluation of frontier free models, not fine-tuning.

2. **`defihack.json` — 389 real historical DeFi hack incidents.** This is the far more interesting find: each entry has a root-cause category (e.g. "Reentrancy", "Access Control", "Price Manipulation", "Flashloans"), a date, protocol name, **dollar amount lost**, a proof-of-concept link, and (for 331/389 of them) the actual vulnerable code snippet. Real, citable, financially-grounded ground truth — not synthetic or academically-contrived examples.

## Research question

Mirrors Pillar 2's shape (per-category failure-mode breakdown) but adapted to what this data actually supports — **not forced to match**, since the data structure is genuinely different from PrimeVul's:

**Proposed RQ:** *Broken down by real-world root-cause category (reentrancy, access control, price manipulation, flashloan exploits, etc.), how well do free open-weight LLMs detect vulnerabilities in code from actual historical DeFi hacks — and does detection accuracy correlate with the financial scale of the exploit (i.e., are LLMs systematically worse at catching the *expensive* bugs)?* That last clause is a novel hook this data uniquely supports (PrimeVul has no financial-impact field) — worth checking whether it holds before committing to it as a headline finding.

**Category distribution checked** (of 331 incidents with code): Flashloans (91), Insufficient validation (56), Access Control (53), Price Manipulation (53), Business Logic Flaw (50), Reentrancy (40), Incorrect logic (27), ERC20 (22), Dex/AMM (20) — enough in the top ~8-9 categories for a stratified sample comparable in scale to Pillar 2's (some incidents carry multiple category tags simultaneously, e.g. "Dex/AMM, Insufficient validation, Reentrancy" — messier than PrimeVul's formal CWE taxonomy, a real limitation to disclose, not hide).

**Real limitation found (disclosed, not glossed over): no natural "patched" counterpart.** Unlike PrimeVul, `defihack.json` doesn't include a fixed/patched version of each exploited contract, so we can't replicate Pillar 2's exact vulnerable/patched-pair design. Planned adaptation: report per-category **recall** (does the model flag the real, known-vulnerable code) as the primary metric, and use `final_dataset`'s balanced safe-labeled examples (from GPTScan-Top200, not per-category-matched) as a **general false-positive-rate baseline** to contextualize recall — an honest adaptation given what's actually available, not a like-for-like replication of Pillar 2's paired design.

## Redundancy check (second pass — higher confidence now, still not 100%)

Tried a second, independent search plus a direct fetch attempt (blocked by paywall both times — MDPI and ResearchGate both returned 403). Best available signal from abstract/summary-level sources: EVuLLM's paper is centered on fine-tuning + parameter-efficient adaptation (QLoRA) + ensemble prompt engineering + RAG, with the headline claim being that fine-tuned *small* open models "surpass the performance of larger proprietary models" — which implies they likely ran zero-shot proprietary models only as a **baseline comparison point** for that claim, not as the paper's own systematic focus. No indication anywhere found of a per-root-cause-category zero-shot breakdown across multiple frontier free/open models, and no indication they used `defihack.json`'s financial-loss field as an analysis axis at all.

**Confidence level: reasonably high this angle is open, not fully certain** (paywall blocks full-text verification). Should re-check once more right before locking the final RQ for write-up, since a paywall block isn't the same as confirmed absence.

## Target venues

- **ReScience C** (rolling, no deadline) — realistic primary target.
- ACM CCS's DeFi'26 workshop deadline (Aug 7, 2026) already unreachable given sequencing; noted for future cycles only.

## Sample built (`code/build_subsample.py`, run, working)

**96 vulnerable incidents across 8 categories (12 each: Access Control, Flashloans, Business Logic Flaw, Insufficient validation, Reentrancy, Incorrect logic, Price Manipulation, ERC20) + 96 benign baseline samples from GPTScan-Top200** = 192 rows, saved to `data/pillar3_subsample.jsonl`.

Note the real category counts differ from the earlier estimate once multi-label incidents are assigned to a single *primary* tag (first-listed) to avoid double-counting: Access Control (46) and Business Logic Flaw (42) turned out bigger than initially estimated, Flashloans dropped from the largest category to tied-second (42) — worth remembering the "top categories" list changes depending on how multi-label ties are broken, a modeling choice to defend in the writeup.

**Financial-loss data quality check (for the "correlates with $ lost" hook):** only 66/96 (69%) of sampled vulnerable incidents have a loss figure at all, and the values are inconsistently formatted — some in USD ("$1.1 M"), some in native token amounts ("115 BNB", "1,078 BNB") needing conversion at time-of-hack exchange rates to compare. This secondary angle is viable but needs real data-cleaning work before it can be trusted; flagged honestly rather than assumed to just work.

## Status

- [x] EVuLLM cloned and inspected — found the real dataset structure (two datasets, not one; defihack.json is the interesting one).
- [x] Category distribution checked, sample design sketched and **built** (192 rows, real data).
- [x] Redundancy check done twice (see above) — reasonably confident, not certain.
- [ ] Financial-loss field needs cleaning/normalization (currency conversion) before the "$-lost correlation" angle can be trusted.
- [ ] No Groq calls yet — sequenced after Pillar 2 and Pillar 1's Arm A/B, consistent with not competing for the same daily per-model token budgets.

Still the lowest-priority pillar per the "stay flexible" decision, but now has a real, sampled dataset ready to go the moment Groq budget frees up — not just a plan.
