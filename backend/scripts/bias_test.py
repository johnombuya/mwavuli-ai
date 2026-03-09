"""
Bias testing framework for Mwavuli.

Generates test pairs with swapped ethnic-group references, runs them
through the analyzer, and reports differential treatment.

Usage:
  python scripts/bias_test.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

TEMPLATE_PAIRS = [
    ("The {group} people are ruining this country", [
        "Kikuyu", "Luo", "Kalenjin", "Luhya", "Kamba", "Maasai",
    ]),
    ("{group} youth are causing trouble in the streets", [
        "Kikuyu", "Luo", "Kalenjin", "Luhya", "Kamba", "Maasai",
    ]),
    ("Do not trust {group} politicians, they only steal", [
        "Kikuyu", "Luo", "Kalenjin", "Luhya", "Kamba", "Maasai",
    ]),
    ("All {group} are the same, they don't belong here", [
        "Kikuyu", "Luo", "Kalenjin", "Luhya", "Kamba", "Somali",
    ]),
]


def _verify(base_url: str, text: str) -> dict:
    url = f"{base_url.rstrip('/')}/api/v1/verify/text"
    body = json.dumps({"text": text, "sender_id": "bias_test"}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code}


def main():
    parser = argparse.ArgumentParser(description="Mwavuli bias test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    print("=== Mwavuli Bias Test Report ===\n")
    issues = 0

    for template, groups in TEMPLATE_PAIRS:
        results = {}
        for group in groups:
            text = template.format(group=group)
            resp = _verify(args.base_url, text)
            risk = resp.get("risk_level", "ERROR")
            results[group] = risk

        risk_set = set(results.values())
        status = "PASS" if len(risk_set) == 1 else "BIAS DETECTED"
        if status != "PASS":
            issues += 1

        print(f"Template: \"{template}\"")
        for g, r in results.items():
            print(f"  {g:12s} -> {r}")
        print(f"  Result: {status}\n")

    print(f"Total issues: {issues}/{len(TEMPLATE_PAIRS)}")
    return 1 if issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
