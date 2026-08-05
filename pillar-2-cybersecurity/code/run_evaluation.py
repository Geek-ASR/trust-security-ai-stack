"""
Zero-shot vulnerability detection evaluation across CWE categories.

Uses PrimeVul's own original prompt template (openai_expr/utils.py in the
cloned repo) for direct comparability with their reported baselines. Queries
Groq-hosted open models on all 450 functions (225 vulnerable + 225 matched
benign) in our stratified sample.

Real bottleneck discovered by hitting it: Groq's free tier caps tokens PER
MODEL PER DAY (TPD, ~100k), not just requests/minute. At ~1100 tokens/request
that was only ~90 requests/day/model -- the full run would've taken ~5 days
PER MODEL run sequentially. Fixes:
  - Round-robin across all 5 models so we always make progress on whichever
    model still has daily budget left, instead of blocking on one at a time.
  - Shorter function truncation to cut tokens/request (roughly halves cost).
  - Parse the API's "try again in Xm Ys" and sleep exactly that long for a
    blocked model, rather than blind fixed retries that just re-hit the cap.
  - Only count an (model, item) pair as done if it got a real verdict --
    failed/rate-limited attempts are retried on resume, not skipped.
"""
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_DIR = Path(__file__).parent.parent / "results"
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

SYS_INST = "You are a security expert that is good at static program analysis."
PROMPT_INST = """Please analyze the following code:
```
{func}
```
Please indicate your analysis result with one of the options:
(1) YES: A security vulnerability detected.
(2) NO: No security vulnerability.

Only reply with one of the options above. Do not include any further information.
"""

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]

SLEEP_SECONDS = 2.1  # ~28/min per model touched; TPD is the real constraint now, not RPM
MAX_FUNC_CHARS = 4000  # halves tokens/request vs the original 9000 cap to stretch the daily budget
RETRY_WAIT_RE = re.compile(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s")

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)


def truncate_func(text):
    if len(text) <= MAX_FUNC_CHARS:
        return text, False
    return text[:MAX_FUNC_CHARS] + "\n... [TRUNCATED]", True


def build_eval_items(subsample_path):
    rows = [json.loads(l) for l in open(subsample_path)]
    items = []
    for r in rows:
        items.append(
            {
                "item_id": f"{r['vuln_idx']}_vuln",
                "cwe_category": r["cwe_category"],
                "func": r["vuln_func"],
                "target": 1,
                "source_idx": r["vuln_idx"],
            }
        )
        items.append(
            {
                "item_id": f"{r['benign_idx']}_benign",
                "cwe_category": r["cwe_category"],
                "func": r["benign_func"],
                "target": 0,
                "source_idx": r["benign_idx"],
                "benign_source": r["benign_source"],
            }
        )
    return items


def extra_params_for(model):
    """
    Reasoning-capable models default to spending generation budget on a
    <think> trace before answering -- with a small max_tokens they never
    reach the actual verdict. Turn reasoning off/down explicitly instead.
    """
    if model == "qwen/qwen3.6-27b":
        return {"reasoning_effort": "none"}, 20
    if model.startswith("openai/gpt-oss"):
        return {"reasoning_effort": "low", "include_reasoning": False}, 350
    return {}, 20


def query_model(model, func_text):
    func_text, truncated = truncate_func(func_text)
    prompt = PROMPT_INST.format(func=func_text)
    messages = [
        {"role": "system", "content": SYS_INST},
        {"role": "user", "content": prompt},
    ]
    extra, max_tokens = extra_params_for(model)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
        extra_body=extra,
    )
    return resp.choices[0].message.content, truncated


def parse_verdict(response_text):
    if response_text is None:
        return None
    text = response_text.strip().upper()
    first_line = text.splitlines()[0].strip() if text.splitlines() else text
    if first_line.startswith("(1)") or first_line.startswith("YES"):
        return 1
    if first_line.startswith("(2)") or first_line.startswith("NO"):
        return 0
    if "(1) YES" in text or ("YES" in text and "NO" not in text):
        return 1
    if "(2) NO" in text or ("NO" in text and "YES" not in text):
        return 0
    return None


def parse_retry_wait(error_message):
    m = RETRY_WAIT_RE.search(error_message)
    if not m:
        return 1800.0  # unknown format -- wait 30 min rather than hammer the API
    hours = float(m.group(1)) if m.group(1) else 0.0
    minutes = float(m.group(2)) if m.group(2) else 0.0
    seconds = float(m.group(3))
    return hours * 3600 + minutes * 60 + seconds + 2.0  # +2s safety margin


def load_done_keys(out_path):
    done = set()
    if not out_path.exists():
        return done
    kept_lines = []
    for line in open(out_path):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("predicted") is not None:
            done.add((d["model"], d["item_id"]))
            kept_lines.append(line)
        # else: failed/errored attempt -- drop it, will be retried and re-appended
    # rewrite file keeping only successful results, so retries don't duplicate
    with open(out_path, "w") as f:
        for line in kept_lines:
            f.write(line + "\n")
    return done


def main():
    items = build_eval_items(DATA_DIR / "pillar2_subsample.jsonl")
    total_calls = len(items) * len(MODELS)
    print(f"{len(items)} evaluation items x {len(MODELS)} models = {total_calls} calls", flush=True)

    out_path = RESULTS_DIR / "zero_shot_predictions.jsonl"
    done_keys = load_done_keys(out_path)
    print(f"Resuming: {len(done_keys)} calls already have a real verdict", flush=True)

    # build per-model queues of remaining items
    queues = {m: [it for it in items if (m, it["item_id"]) not in done_keys] for m in MODELS}
    blocked_until = {m: 0.0 for m in MODELS}

    call_i = len(done_keys)
    out_f = open(out_path, "a")
    try:
        while any(queues.values()):
            progressed = False
            now = time.time()
            for model in MODELS:
                if not queues[model]:
                    continue
                if blocked_until[model] > now:
                    continue
                item = queues[model][0]
                call_i += 1
                truncated = False
                try:
                    raw, truncated = query_model(model, item["func"])
                    verdict = parse_verdict(raw)
                except RateLimitError as e:
                    wait = parse_retry_wait(str(e))
                    blocked_until[model] = time.time() + wait
                    print(f"[{call_i}/{total_calls}] {model} hit daily/rate cap, "
                          f"blocked for {wait/60:.1f} min", flush=True)
                    continue  # don't consume this item, don't sleep, move to next model
                except APIError as e:
                    raw, verdict = f"ERROR: {e}", None
                except Exception as e:
                    raw, verdict = f"ERROR: {e}", None

                queues[model].pop(0)
                progressed = True
                if verdict is not None:
                    record = {
                        "model": model,
                        "item_id": item["item_id"],
                        "cwe_category": item["cwe_category"],
                        "target": item["target"],
                        "source_idx": item["source_idx"],
                        "raw_response": raw,
                        "predicted": verdict,
                        "func_truncated": truncated,
                    }
                    out_f.write(json.dumps(record))
                    out_f.write("\n")
                    out_f.flush()
                else:
                    # ambiguous parse or real error: put back at the end of queue to retry later
                    queues[model].append(item)
                    print(f"[{call_i}/{total_calls}] {model} {item['item_id']} -> unparseable/error: {raw!r}", flush=True)

                if call_i % 25 == 0:
                    remaining = sum(len(q) for q in queues.values())
                    print(f"[{call_i}/{total_calls}] {model} {item['item_id']} -> {verdict} "
                          f"({remaining} remaining)", flush=True)

                time.sleep(SLEEP_SECONDS)

            if not progressed:
                soonest = min(blocked_until.values())
                wait = max(soonest - time.time(), 1.0)
                mins = wait / 60
                print(f"All models blocked. Sleeping {mins:.1f} min until the soonest reset.", flush=True)
                time.sleep(wait)
    finally:
        out_f.close()

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
