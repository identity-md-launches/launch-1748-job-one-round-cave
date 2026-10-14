#!/usr/bin/env python3
"""Bind an explicit gas budget and headroom policy to exact historical calls."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'budget_gas_cap', HERE.parent / 'gas-cap-rehearsal' / 'gas_cap.py')
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
core, binding = cap.core, cap.binding
SCHEMA = 'gas-budget-evidence-v1'
POLICY = 'gas-budget-policy-v1'
LIMITS = (
    'This compares an unauthenticated historical provider estimate with a reviewer-chosen '
    'allowance and margin, after checking exact expected baseline/capped return bytes. '
    'The arithmetic is a policy comparison, not consumed gas, a recommended gas limit, '
    'transaction approval, ABI semantics, authority, sender availability, chain authenticity '
    'or a prediction of future execution. A contract can branch on gasleft(). Calls are '
    'independent at one historical state. Public source names are attribution, not verified '
    'provider independence, especially through a contributor relay. Nothing is sent.')


class BudgetRPC(core.RPC):
    METHODS = core.RPC.METHODS | {'eth_estimateGas'}


def policy(value):
    core.require(isinstance(value, dict) and set(value) ==
                 {'schema', 'request', 'minimum_headroom_bps'}, 'invalid budget policy fields')
    core.require(value['schema'] == POLICY, 'unsupported budget policy schema')
    margin = value['minimum_headroom_bps']
    core.require(type(margin) is int and 0 <= margin <= 100_000,
                 'minimum_headroom_bps must be an integer from 0 through 100000')
    return {'schema': POLICY, 'request': cap.request(value['request']),
            'minimum_headroom_bps': margin}


def estimate_outcome(value):
    core.require(isinstance(value, dict) and len(value) == 1,
                 'estimate outcome requires exactly result or error')
    if 'result' in value:
        gas = core.quantity(value['result'])
        core.require(0 < gas < 2**64, 'estimate must be positive and below uint64')
        return {'result': hex(gas)}
    core.require('error' in value, 'estimate outcome lacks result or error')
    return cap.outcome(value)


def validate(value):
    core.require(isinstance(value, dict) and set(value) ==
                 {'schema', 'cap_evidence', 'estimate'} and value['schema'] == SCHEMA,
                 'invalid budget evidence fields or schema')
    cap.validate(value['cap_evidence'])
    estimate = value['estimate']
    core.require(isinstance(estimate, dict) and set(estimate) ==
                 {'chain_id', 'source', 'transport', 'call', 'block', 'outcome', 'recheck'},
                 'invalid estimate fields')
    core.require(type(estimate['chain_id']) is int and estimate['chain_id'] == 1,
                 'estimate requires Ethereum mainnet')
    core.require(estimate['source'] in core.ENDPOINTS and
                 estimate['transport'] in ('public-rpc', 'contributor-relay'),
                 'unsupported estimate provenance')
    core.require(isinstance(estimate['call'], dict) and set(estimate['call']) ==
                 {'from', 'to', 'data', 'value'}, 'estimate requires an explicit exact call')
    call = core.transaction(estimate['call'])
    block = binding.exact_block(estimate['block'])
    core.require(binding.exact_block(estimate['recheck']) == block,
                 'estimate block changed on recheck')
    return dict(estimate, call=call, block=block, recheck=block,
                outcome=estimate_outcome(estimate['outcome']))


def evaluate(evidence, proposed):
    chosen = policy(proposed)
    estimate = validate(evidence)
    capped = cap.evaluate(evidence['cap_evidence'], chosen['request'])
    wanted = chosen['request']
    differences = [key for key in ('chain_id', 'call', 'block')
                   if estimate[key] != wanted[key]]
    report = {'schema': POLICY, 'verdict': 'inconclusive', 'policy': chosen,
              'policy_sha256': binding.digest(chosen),
              'evidence_sha256': binding.digest(evidence),
              'cap_rehearsal': capped, 'estimate_context_differences': differences,
              'estimate': estimate, 'limits': LIMITS}
    if capped['verdict'] in ('request_mismatch', 'return_mismatch') or differences:
        report.update(verdict='mismatch', reason='expected returns or exact call context differ')
    elif capped['verdict'] != 'matched' or 'error' in estimate['outcome']:
        report['reason'] = 'capped rehearsal or provider estimate is inconclusive'
    else:
        gas = core.quantity(estimate['outcome']['result'])
        allowance = int(wanted['gas_limit'])
        margin = chosen['minimum_headroom_bps']
        # Exact ceiling division; no floating point and no automatic policy choice.
        required = (gas * (10_000 + margin) + 9_999) // 10_000
        within = allowance >= required
        report.update(verdict='within_budget' if within else 'over_budget',
                      reason='allowance meets the declared estimate margin' if within else
                             'allowance is below the declared estimate margin',
                      estimate_gas=str(gas), allowance_gas=str(allowance),
                      required_by_policy_gas=str(required),
                      spare_above_estimate_gas=str(allowance - gas),
                      spare_above_policy_gas=str(allowance - required))
    return report


def capture(rpc, proposed):
    chosen = policy(proposed)  # No network before all policy fields are validated.
    wanted = chosen['request']
    evidence = cap.capture(rpc, wanted)
    pin = {'blockHash': wanted['block']['hash'], 'requireCanonical': True}
    try:
        outcome = estimate_outcome({'result': rpc.call(
            'eth_estimateGas', [dict(wanted['call']), pin])})
    except core.RPCError as exc:
        outcome = estimate_outcome({'error': exc.error})
    recheck = core.header(rpc.call('eth_getBlockByNumber', [wanted['block']['number'], False]))
    result = {'schema': SCHEMA, 'cap_evidence': evidence,
              'estimate': {'chain_id': 1, 'source': rpc.endpoint,
                           'transport': 'contributor-relay' if rpc.via_relay else 'public-rpc',
                           'call': dict(wanted['call']), 'block': wanted['block'],
                           'outcome': outcome, 'recheck': recheck}}
    validate(result)
    return result


def exit_code(report):
    return {'within_budget': 0, 'over_budget': 1, 'mismatch': 1,
            'inconclusive': 2}[report['verdict']]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='offline real ZTO evidence and illustrative reviewer policy')
    check = commands.add_parser('check', help='check saved evidence against an explicit budget policy')
    check.add_argument('evidence')
    check.add_argument('policy')
    live = commands.add_parser('live', help='collect exact read-only calls and estimate')
    live.add_argument('policy')
    live.add_argument('--rpc', choices=core.ENDPOINTS, default=core.ENDPOINTS[0])
    live.add_argument('--relay', help='explicit contributor transport, omitted from saved evidence')
    live.add_argument('--save', required=True, help='new workspace-contained evidence path')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            proposed = binding.read_json(HERE / 'zto-budget-policy.json')
            evidence = binding.read_json(HERE / 'zto-budget-evidence.json')
        else:
            proposed = binding.read_json(args.policy)
            policy(proposed)
            if args.command == 'check':
                evidence = binding.read_json(args.evidence)
            else:
                destination = core.workspace_path(args.save)
                core.require(not destination.exists() and destination.parent.is_dir(),
                             'save requires a new file and an existing parent')
                evidence = capture(BudgetRPC(args.rpc, relay=args.relay), proposed)
                raw = (json.dumps(evidence, indent=2, allow_nan=False) + '\n').encode()
                core.require(len(raw) <= binding.LIMIT, 'evidence exceeds 95 KB')
                with destination.open('xb') as handle:
                    handle.write(raw)
        result = evaluate(evidence, proposed)
        print(json.dumps(result, indent=2, allow_nan=False))
        return exit_code(result)
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': POLICY, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
