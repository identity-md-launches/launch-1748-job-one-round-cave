#!/usr/bin/env python3
"""Carry raw ZTO/IMD witnesses in one offline, receiver-reviewed JSON packet."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-witness-quorum'))
import zto_witness_quorum as quorum

replay = quorum.replay
require = replay.require
PACKET_KEYS = {'schema', 'input_token', 'amount', 'slippage_bps', 'captures'}
CAPTURE_KEYS = {'snapshot', 'quoter'}
MAX_BYTES = 100_000


def canonical(packet):
    return json.dumps(packet, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def validate_packet(packet):
    require(type(packet) is dict and set(packet) == PACKET_KEYS, 'unexpected packet fields')
    require(packet['schema'] == 'zto-witness-packet-v1', 'unexpected packet schema')
    require(type(packet['input_token']) is str and packet['input_token'] in ('ZTO', 'IMD'),
            'input token must be ZTO or IMD')
    require(type(packet['amount']) is str and len(packet['amount']) <= 120 and
            re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', packet['amount']) is not None,
            'amount must be a plain decimal string')
    require(type(packet['slippage_bps']) is int and 0 <= packet['slippage_bps'] <= 9999,
            'slippage bps must be an integer from 0 to 9999')
    captures = packet['captures']
    require(type(captures) is list and 2 <= len(captures) <= 8,
            'packet needs 2..8 raw capture pairs')
    for capture in captures:
        require(type(capture) is dict and set(capture) == CAPTURE_KEYS,
                'capture must contain exactly snapshot and quoter')
        require(all(type(capture[key]) is dict for key in CAPTURE_KEYS),
                'captures must contain inline objects, never paths or URLs')
    require(len(canonical(packet)) <= MAX_BYTES, 'canonical packet exceeds 100 KB')
    return packet


def review(packet, policy, minimum_distinct_groups, expected_packet_sha256=None):
    """Load no capture files: recompute from inline data and separately supplied policy."""
    validate_packet(packet)
    quorum.policy_tool.validate_policy(policy)
    require(packet['input_token'] == policy['input_token'],
            'packet direction differs from receiver policy')
    require(type(minimum_distinct_groups) is int and 2 <= minimum_distinct_groups <= 8,
            'minimum distinct groups must be an integer from 2 to 8')
    require(len(packet['captures']) >= minimum_distinct_groups,
            'capture count is below receiver quorum')
    packet_hash = replay.digest(packet)
    if expected_packet_sha256 is not None:
        require(type(expected_packet_sha256) is str and
                re.fullmatch(r'[0-9a-f]{64}', expected_packet_sha256) is not None,
                'expected packet hash must be lowercase SHA-256')
        require(packet_hash == expected_packet_sha256, 'packet differs from receiver fingerprint')
    # Internal deterministic references are map keys, never filesystem paths.
    values, candidates = {}, []
    for index, capture in enumerate(packet['captures']):
        refs = {key: f'capture/{index}/{key}' for key in ('snapshot', 'quoter')}
        candidates.append(refs)
        values.update({refs[key]: capture[key] for key in refs})
    request = {'schema': 'zto-witness-quorum-request-v1', 'policy': policy,
               'minimum_distinct_groups': minimum_distinct_groups,
               'amount': packet['amount'], 'slippage_bps': packet['slippage_bps'],
               'candidates': candidates}
    result = quorum.evaluate(request, loader=values.__getitem__)
    return {'schema': 'zto-witness-packet-report-v1', 'status': result['status'],
            'packet_sha256': packet_hash, 'receiver_fingerprint_checked': expected_packet_sha256 is not None,
            'receiver_policy_sha256': replay.digest(policy),
            'captures_sha256': [{key: replay.digest(capture[key]) for key in ('snapshot', 'quoter')}
                                for capture in packet['captures']],
            'bound_released': result['bound_released'], 'bound': result['bound'],
            'reasons': result['reasons'], 'quorum_report': result,
            'limitations': ['The packet carries evidence, never receiver policy or transaction authority.',
                            'SHA-256 identifies canonical JSON content; it does not authenticate an RPC or sender.',
                            *result['limitations']]}


def pack(request, loader=replay.read_json):
    """Read each named file once, retain raw evidence, and check it before packaging."""
    quorum.validate_request(request)
    captures = [{key: copy.deepcopy(loader(candidate[key])) for key in ('snapshot', 'quoter')}
                for candidate in request['candidates']]
    packet = {'schema': 'zto-witness-packet-v1', 'input_token': request['policy']['input_token'],
              'amount': request['amount'], 'slippage_bps': request['slippage_bps'],
              'captures': captures}
    # Withheld evidence may still be handed off, but malformed evidence cannot.
    review(packet, request['policy'], request['minimum_distinct_groups'])
    return packet


def demo_inputs():
    request, observation, check = quorum.demo_request()
    values = iter((observation, check, observation, check))
    return pack(request, lambda _: next(values)), request['policy']


def demo():
    packet, policy = demo_inputs()
    result = review(packet, policy, 2, replay.digest(packet))
    result['mode'] = 'offline_real_historical_single_source_packet'
    result['canonical_packet_bytes'] = len(canonical(packet))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--pack', metavar='REQUEST_JSON')
    mode.add_argument('--packet', metavar='PACKET_JSON')
    parser.add_argument('--policy', help='separately receiver-authored policy JSON')
    parser.add_argument('--minimum-distinct-groups', type=int)
    parser.add_argument('--expected-packet-sha256', help='trusted canonical JSON fingerprint, not a signature')
    args = parser.parse_args(argv)
    controls = (args.policy, args.minimum_distinct_groups, args.expected_packet_sha256)
    try:
        if args.demo:
            require(all(v is None for v in controls), '--demo cannot be combined with receiver controls')
            result = demo()
        elif args.pack:
            require(all(v is None for v in controls), '--pack takes controls from its request')
            packet = pack(replay.read_json(args.pack))
            # A single compact JSON file stays within the inherited 100 KB reader limit.
            require(len(canonical(packet)) + 1 <= MAX_BYTES, 'serialized packet exceeds 100 KB')
            print(canonical(packet).decode('ascii'))
            return 0
        else:
            require(args.policy is not None and args.minimum_distinct_groups is not None,
                    'supply separate --policy and --minimum-distinct-groups')
            result = review(replay.read_json(args.packet), replay.read_json(args.policy),
                            args.minimum_distinct_groups, args.expected_packet_sha256)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if args.demo or result['bound_released'] else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
