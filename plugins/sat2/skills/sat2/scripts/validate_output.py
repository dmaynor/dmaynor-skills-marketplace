#!/usr/bin/env python3
"""Validate sat2.output.v1; exit 0 valid, 1 invalid, 2 IO/usage error."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

MODES = {'BREACH_DETECTION', 'CRASH_ANALYSIS', 'FIX_VERIFICATION', 'STATEMENT_ANALYSIS', 'GENERAL_HYPOTHESIS'}

def validate(doc: Any) -> None:
    """Raise ValueError when an output violates the structural contract."""
    def require(ok: bool, message: str) -> None:
        if not ok:
            raise ValueError(message)
    def obj(value: Any) -> dict:
        require(isinstance(value, dict), 'expected object')
        return value
    def text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())
    def seq(value: Any) -> list:
        require(isinstance(value, list), 'expected array')
        return value
    def probability(value: Any) -> bool:
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
    d = obj(doc)
    require(d.get('schema') == 'sat2.output.v1', 'invalid schema')
    if 'error' in d:
        require(set(d) == {'schema', 'error'}, 'error must be exclusive')
        e = obj(d['error'])
        require(e.get('code') == 'bad_input' and text(e.get('message')), 'invalid error')
        return
    require(text(d.get('claim')) and d.get('mode') in MODES, 'invalid claim/mode')
    gate = obj(d.get('gate'))
    require(type(gate.get('passed')) is bool and text(gate.get('note')), 'invalid gate')
    c = obj(d.get('completion'))
    require(type(c.get('discriminated')) is bool and text(c.get('statement')), 'invalid completion')
    remaining = seq(c.get('remaining_tests'))
    require(all(text(x) for x in remaining) and len(set(remaining)) == len(remaining), 'invalid remaining IDs')
    if d.get('result_kind') == 'direct':
        r = obj(d.get('direct_result'))
        require(not gate['passed'] and text(r.get('result')) and text(r.get('source')), 'invalid direct result')
        require(c.get('condition') == 'direct' and c['discriminated'] and not remaining, 'invalid direct completion')
        require(not d.get('hypotheses'), 'direct output must not invent hypotheses')
        return
    require(d.get('result_kind') == 'analysis' and gate['passed'], 'invalid analysis gate')
    require(bool(seq(gate.get('conditions'))), 'missing gate condition')
    require(all(x in {'competition','adversarial_surface','downstream_action'} for x in gate['conditions']), 'invalid gate condition')
    hs = seq(d.get('hypotheses'))
    require(len(hs) >= 5, 'need >=5 hypotheses')
    ids: set[str] = set()
    cats: set[str] = set()
    for value in hs:
        h = obj(value)
        require(all(text(h.get(k)) for k in ('id','text','category','prior_basis','falsified_by')), 'incomplete hypothesis')
        require(h['id'] not in ids, 'duplicate hypothesis ID')
        ids.add(h['id']); cats.add(h['category'])
        require(probability(h.get('prior')), 'invalid prior')
    require({'obvious','null','uncomfortable'} <= cats, 'missing required categories')
    tests = seq(d.get('discriminating_tests'))
    require(bool(tests), 'missing discriminating tests')
    test_ids: set[str] = set()
    for index, value in enumerate(tests, 1):
        t = obj(value)
        require(all(text(t.get(k)) for k in ('id','action','exit_condition')), 'incomplete test')
        require(t['id'] not in test_ids, 'duplicate test ID'); test_ids.add(t['id'])
        refs = seq(t.get('discriminates'))
        require(all(text(x) for x in refs), 'invalid hypothesis references')
        require(len(set(refs)) >= 2 and set(refs) <= ids, 'invalid discrimination references')
        require(type(t.get('order')) is int and t['order'] == index, 'invalid test order')
    require(set(remaining) <= test_ids, 'unknown remaining test')
    cond = c.get('condition')
    require(cond in {'a','b','c','unresolved'}, 'invalid completion condition')
    require((cond == 'a') == c['discriminated'], 'inconsistent completion')
    require((not remaining) if cond == 'a' else bool(remaining), 'inconsistent remaining tests')
    if cond == 'b':
        for t in tests:
            if t['id'] in remaining:
                require(text(t.get('owner')) and text(t.get('queue_evidence')), 'queue requires owner and acknowledgment')
    if cond == 'c':
        require(text(c.get('budget_exhaustion_source')), 'caller budget declaration required')
    a = obj(d.get('assessment'))
    require(all(text(a.get(k)) for k in ('conclusion','confidence_term','basis')), 'invalid assessment')
    bounds = seq(a.get('confidence_range'))
    require(len(bounds) == 2 and all(probability(x) for x in bounds) and bounds[0] <= bounds[1], 'invalid confidence range')
    for key in ('assumptions','limitations'):
        require(bool(seq(d.get(key))) and all(text(x) for x in d[key]), 'missing '+key)
    ach = obj(d.get('ach'))
    require(type(ach.get('included')) is bool and text(ach.get('reason')), 'invalid ACH')
    if ach['included']:
        require(ach.get('trigger') in {'explicit_request','planned_evidence_round','programmatic_scores_requested'}, 'invalid ACH trigger')

def main() -> int:
    """Read a UTF-8 JSON document and report validity without tracebacks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path)
    args = parser.parse_args()
    try:
        raw = args.file.read_text(encoding='utf-8') if args.file else sys.stdin.read()
    except (OSError, UnicodeError) as exc:
        print(f'IO ERROR: {exc}', file=sys.stderr); return 2
    try:
        validate(json.loads(raw))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f'INVALID: {exc}', file=sys.stderr); return 1
    print('VALID'); return 0

if __name__ == '__main__':
    raise SystemExit(main())
