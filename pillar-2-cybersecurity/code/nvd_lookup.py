"""
Query NVD's public API for the official CWE assignment of each unique CVE ID
in our sample, to independently validate PrimeVul/BigVul's CWE tags against
the authoritative current record (not just BigVul's ~2019-era scrape).

Respects NVD's unauthenticated rate limit (5 requests / 30s) with a safety
margin. Saves incrementally so a partial run isn't wasted.
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = DATA_DIR / "nvd_cwe_lookup.json"
SLEEP_SECONDS = 7  # ~4.3 req/30s, safely under the 5/30s unauthenticated limit


def fetch_nvd(cve_id):
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "independent-research-script"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return {"status": "not_found", "cwes": []}
    cve = vulns[0]["cve"]
    cwes = []
    for w in cve.get("weaknesses", []):
        for d in w.get("description", []):
            if d.get("value", "").startswith("CWE-"):
                cwes.append({"value": d["value"], "type": w.get("type")})
    return {"status": "ok", "cwes": cwes, "vuln_status": cve.get("vulnStatus")}


def main():
    subsample = [json.loads(l) for l in open(DATA_DIR / "pillar2_subsample_with_cve.jsonl")]
    unique_cves = sorted({r["bigvul_cve_id"] for r in subsample if r.get("bigvul_cve_id")})
    print(f"{len(unique_cves)} unique CVEs to look up", flush=True)

    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text())
        print(f"Resuming: {len(results)} already fetched", flush=True)

    remaining = [c for c in unique_cves if c not in results]
    for i, cve_id in enumerate(remaining):
        try:
            results[cve_id] = fetch_nvd(cve_id)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"Rate limited on {cve_id}, sleeping 30s extra", flush=True)
                time.sleep(30)
                try:
                    results[cve_id] = fetch_nvd(cve_id)
                except Exception as e2:
                    results[cve_id] = {"status": "error", "error": str(e2)}
            else:
                results[cve_id] = {"status": "error", "error": str(e)}
        except Exception as e:
            results[cve_id] = {"status": "error", "error": str(e)}

        if (i + 1) % 10 == 0 or i == len(remaining) - 1:
            OUT_PATH.write_text(json.dumps(results, indent=2))
            print(f"[{i+1}/{len(remaining)}] saved progress ({cve_id})", flush=True)

        time.sleep(SLEEP_SECONDS)

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Done. Total results: {len(results)}", flush=True)


if __name__ == "__main__":
    main()
