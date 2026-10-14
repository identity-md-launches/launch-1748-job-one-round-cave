#!/usr/bin/env python3
"""Recompute runtime proof and exact gas-budget policy at one historical block."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


code = module('budget_proof_code', ROOT / 'line-3/tools/code-target-proofs/code_target_proofs.py')
budget = module('budget_proof_call', ROOT / 'line-4/tools/gas-budget/gas_budget.py')
alignment = module('budget_proof_alignment', HERE.parent / 'evidence-alignment/evidence_alignment.py')


def evaluate(bundle, evidence, policy):
    identity = code.evaluate(bundle, [])
    rehearsal = budget.evaluate(evidence, policy)
    request = rehearsal['policy']['request']
    same = (alignment.context(identity['chain_id'], identity['source_target'], identity['code_block'])
            == alignment.context(request['chain_id'], request['call']['to'], request['block']))
    joined = same and rehearsal['verdict'] == 'within_budget'
    reasons = ([] if same else ['code-call-context-mismatch'])
    if rehearsal['verdict'] != 'within_budget':
        reasons.append('gas-budget-' + rehearsal['verdict'])
    return {'schema': 'proof-gas-budget-context-v1',
            'status': 'historical_context_joined' if joined else 'withheld',
            'context_aligned': same, 'reasons': reasons,
            'code_identity': identity, 'gas_budget': rehearsal,
            'proof_input_sha256': budget.binding.digest(bundle),
            'joined_request': request if joined else None,
            'transaction_approved': False,
            'limits': 'Historical evidence association only. Runtime inclusion is relative to '
                      'an unauthenticated supplied header. Calls and estimates are provider claims, '
                      'not execution proofs. A chosen margin does not establish consumed gas, a safe '
                      'transaction limit, semantics, sender authority, current or future execution. '
                      'Unresolved dependencies remain in code_identity. Nothing is signed or sent.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', default=str(HERE.parent / 'proof-gas-cap/zto-proof.json'))
    parser.add_argument('--evidence', default=str(ROOT / 'line-4/tools/gas-budget/zto-budget-evidence.json'))
    parser.add_argument('--policy', default=str(ROOT / 'line-4/tools/gas-budget/zto-budget-policy.json'))
    args = parser.parse_args()
    try:
        result = evaluate(*(budget.binding.read_json(path)
                            for path in (args.proof, args.evidence, args.policy)))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['status'] == 'historical_context_joined' else 2
    except (ValueError, KeyError, TypeError, OSError, AttributeError, RecursionError) as exc:
        print(json.dumps({'status': 'invalid', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
