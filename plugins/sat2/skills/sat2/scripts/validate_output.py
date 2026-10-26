#!/usr/bin/env python3
"""Validate a sat2 machine output document against the sat2.output.v1 invariants.

Usage:
    validate_output.py --file out.json      # or pipe JSON on stdin
    echo '<json>' | validate_output.py

Exit codes: 0 = valid; 1 = invalid; 2 = usage/IO error.
"""
import argparse
import json
import sys

REQUIRED_KEYS = {"schema", "claim", "gate", "hypotheses", "assessment", "completion"}
CATEGORIES = {"obvious", "null", "uncomfortable", "malicious", "systemic"}
COMPLETION_CONDITIONS = {"a", "b", "c"}
ANCHOR_HINTS = ("measured", "historical", "document", "rate", "frequency")


def fail(msg):
    print(f"INVALID: {msg}")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    args = ap.parse_args()

    try:
        if args.file:
            with open(args.file) as fh:
                doc = json.load(fh)
        else:
            doc = json.load(sys.stdin)
    except Exception as exc:
        return fail(f"not parseable JSON: {exc}")

    if not isinstance(doc, dict):
        return fail("top level is not an object")

    if "error" in doc:
        missing = REQUIRED_KEYS - {"schema", "claim"}
        if missing & set(doc):
            return fail(f"error document also contains analysis keys: {sorted(missing & set(doc))}")
        err = doc.get("error") or {}
        if not err.get("code"):
            return fail("error document lacks error.code")
        print("VALID (error document)")
        return 0

    missing = REQUIRED_KEYS - set(doc)
    if missing:
        return fail(f"missing required keys: {sorted(missing)}")
    if doc["schema"] != "sat2.output.v1":
        return fail(f"schema must be sat2.output.v1, got {doc['schema']!r}")

    hypos = doc["hypotheses"]
    if not isinstance(hypos, list) or len(hypos) < 5:
        return fail(f"hypotheses must be a list of >=5, got {len(hypos) if isinstance(hypos, list) else type(hypos).__name__}")

    cats = set()
    for h in hypos:
        for field in ("id", "text", "category", "prior", "prior_basis", "falsified_by"):
            if not h.get(field):
                return fail(f"hypothesis {h.get('id', '?')} missing field {field}")
        if h["category"] not in CATEGORIES:
            return fail(f"hypothesis {h['id']}: unknown category {h['category']!r}")
        cats.add(h["category"])
        try:
            p = float(h["prior"])
        except (TypeError, ValueError):
            return fail(f"hypothesis {h['id']}: prior not numeric")
        if not 0.0 <= p <= 1.0:
            return fail(f"hypothesis {h['id']}: prior {p} outside [0,1]")
        basis = str(h["prior_basis"]).lower()
        if not any(k in basis for k in ANCHOR_HINTS) and "subjective prior" not in basis:
            print(f"WARN: hypothesis {h['id']} prior_basis names no anchor and is not labeled 'subjective prior'")

    for required in ("null", "uncomfortable"):
        if required not in cats:
            return fail(f"hypotheses missing required category: {required}")

    completion = doc["completion"]
    cond = completion.get("condition")
    if cond not in COMPLETION_CONDITIONS:
        return fail(f"completion.condition must be a|b|c, got {cond!r}")
    remaining = completion.get("remaining_tests") or []
    if not completion.get("discriminated") and not remaining:
        return fail("completion.discriminated is false but remaining_tests is empty")

    tests = doc.get("discriminating_tests") or []
    if tests:
        first = tests[0]
        if len(first.get("discriminates") or []) < 2:
            return fail("discriminating_tests[0] must discriminate >=2 hypotheses")
        if not first.get("exit_condition"):
            return fail("discriminating_tests[0] missing exit_condition")

    ach = doc.get("ach") or {}
    if ach.get("included") and not (ach.get("reason") or "").strip():
        return fail("ach.included=true requires ach.reason naming the gate condition")

    print("VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
