# Research Program: Trust and Security Across the AI Stack

**Goal:** produce 2-3+ real, honestly-reported research outputs to support a masters application, submitted within the ~3-4 month window from July 2026.

**Shared theme, not shared method:** three pillars, each asking a version of "how much can we trust AI systems, and how well can AI systems help secure other systems" — but each using whatever method fits its own subfield, not a forced identical methodology. Connected by theme and (where it fits naturally) a "reasoning-toggle" evaluation lever, not required to match.

| Pillar | Layer of trust | Status | Priority |
|---|---|---|---|
| [1. AI Safety](pillar-1-ai-safety/README.md) | Social/interaction — does a model tell the truth under social pressure? | Scoped, zero-cost pipeline designed, blocked on Groq key | **1st — in progress** |
| [2. Cybersecurity + LLMs](pillar-2-cybersecurity/README.md) | Software/code — can LLMs detect real vulnerabilities against ground truth? | Scoped (PrimeVul anchor found) | 2nd — realistic "3rd paper" |
| [3. Blockchain/Distributed + AI](pillar-3-blockchain/README.md) | Decentralized infrastructure — can LLMs audit smart contracts? | Scoped (EVuLLM anchor found) | 3rd — stretch, flexible per user's call |

Per user's decision: stay flexible on whether pillar 3 makes it into the window — better to finish pillars 1-2 solidly than rush all three.

## Budget: $0

User has no budget for API calls and no existing API keys. Real news: **legitimate CS venues here charge no submission/review fees at all** (ReScience C, NeurIPS/ACL/CCS workshops, arXiv are all free) — a venue that charges for review is a predatory-publishing red flag, not something to pay. Money is only realistically relevant later for optional things like conference travel/registration if a paper is accepted for in-person presentation, which is a separate, later decision.

All three pillars are designed around **Groq's free tier** (console.groq.com — no credit card required): it hosts open-weight models (Llama, Qwen3, Gemma2, DeepSeek R1 Distill, OpenAI's open-weight gpt-oss) with fast, genuinely free inference. This is shared infrastructure across all three pillars — one API key, reused everywhere — which is also why pillars 2 and 3 are much cheaper to execute than pillar 1 was to design from scratch.

## What's needed from you

- Create a free Groq account and API key at console.groq.com (email or Google sign-in, no credit card), store it as a local environment variable (e.g. `GROQ_API_KEY`) — never paste it into chat. (Walkthrough already given; waiting on confirmation this is done.)
- Later, for Pillar 1 specifically: hand-label a small (~30-50 example) validation sample so we can report how well our substitute judge model agrees with human judgment.

## Folder map

- `pillar-1-ai-safety/` — ELEPHANT reproduction (`track-A-reproducibility/`) + reasoning-toggle extension (`track-B-extension/`)
- `pillar-2-cybersecurity/` — PrimeVul-based LLM vulnerability detection evaluation
- `pillar-3-blockchain/` — EVuLLM-based smart contract vulnerability detection evaluation
- `literature-notes/` — shared reference notes across pillars
- `.env` — shared `GROQ_API_KEY`, gitignored/local-only, never displayed in chat
