#!/usr/bin/env python3
"""Backfill one missing ERC-20 Approval-event interval without historical state reads."""

import argparse
import json
import math
from pathlib import Path
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'approval-coverage'))
import approval_coverage as coverage

lens = coverage.lens
gate = coverage.gate
SCHEMA = 'approval-event-backfill-v1'
USER_AGENT = 'IdentityMD-Pepeolithic-Line2-ApprovalBackfill/1.0'
ENDPOINTS = ('https://ethereum-rpc.publicnode.com', 'https://eth.drpc.org')
MAX_BYTES = 98_304


class RPC:
    METHODS = {'eth_chainId', 'eth_getBlockByNumber', 'eth_getLogs'}

    def __init__(self, endpoint):
        lens.require(endpoint in ENDPOINTS, 'unsupported public Ethereum endpoint')
        self.endpoint = endpoint
        self.counter = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), lens.NoRedirect())

    def call(self, method, params):
        lens.require(method in self.METHODS, 'RPC method is not read-only allowlisted')
        self.counter += 1
        data = json.dumps({'jsonrpc': '2.0', 'id': self.counter,
                           'method': method, 'params': params}).encode()
        request = urllib.request.Request(self.endpoint, data=data, headers={
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'User-Agent': USER_AGENT,
        })
        with self.opener.open(request, timeout=15) as response:
            raw = response.read(1_000_001)
        lens.require(len(raw) <= 1_000_000, 'RPC response exceeds 1 MB')
        value = json.loads(raw, object_pairs_hook=gate.unique_object)
        lens.require(isinstance(value, dict) and value.get('jsonrpc') == '2.0'
                     and type(value.get('id')) is int and value['id'] == self.counter,
                     'RPC response envelope mismatch')
        lens.require('error' not in value and 'result' in value,
                     'RPC error or missing result: ' + str(value.get('error')))
        return value['result']


def validate_fill(value):
    lens.require(isinstance(value, dict) and value.get('schema') == SCHEMA,
                 'unsupported backfill schema')
    lens.require(value.get('source') in ENDPOINTS and type(value.get('chain_id')) is int
                 and value['chain_id'] == 1, 'invalid source or chain')
    token = value.get('token')
    lens.require(token in lens.TOKENS and value.get('token_address') == lens.TOKENS[token],
                 'invalid token')
    start, end = value.get('from_block'), value.get('to_block')
    lens.require(type(start) is int and type(end) is int and 0 <= start <= end
                 and end-start < lens.MAX_BLOCKS, 'invalid backfill interval')
    block = lens.header(value.get('end_block'))
    lens.require(lens.quantity(block['number']) == end, 'end block number mismatch')
    pairs, decoded = lens.decode_logs(value.get('logs'), lens.TOKENS[token], start, end)
    headers = value.get('log_headers')
    lens.require(isinstance(headers, dict)
                 and set(headers) == {hex(row[0]) for row in decoded},
                 'log header set mismatch')
    for number, _, _, _, _, block_hash in decoded:
        header = lens.header(headers[hex(number)])
        lens.require(lens.quantity(header['number']) == number
                     and header['hash'].lower() == block_hash,
                     'Approval event block hash mismatch')
        if number == end:
            lens.require(header == block, 'end block and log header disagree')
    return pairs


def capture(endpoint, token, start, end):
    lens.require(endpoint in ENDPOINTS and token in lens.TOKENS,
                 'unsupported endpoint or token')
    lens.require(type(start) is int and type(end) is int and 0 <= start <= end
                 and end-start < lens.MAX_BLOCKS, 'invalid backfill interval')
    rpc = RPC(endpoint)
    lens.require(rpc.call('eth_chainId', []) == '0x1', 'expected Ethereum mainnet')
    block = lens.header(rpc.call('eth_getBlockByNumber', [hex(end), False]))
    lens.require(lens.quantity(block['number']) == end, 'RPC returned wrong end block')
    logs = []
    for first in range(start, end + 1, 250):
        last = min(first + 249, end)
        chunk = rpc.call('eth_getLogs', [{'address': lens.TOKENS[token],
                          'topics': [lens.APPROVAL], 'fromBlock': hex(first),
                          'toBlock': hex(last)}])
        lens.decode_logs(chunk, lens.TOKENS[token], first, last)
        logs.extend(chunk)
        lens.require(len(logs) <= lens.MAX_LOGS, 'too many logs; use a smaller interval')
    _, decoded = lens.decode_logs(logs, lens.TOKENS[token], start, end)
    headers = {}
    for number, _, _, _, _, block_hash in decoded:
        key = hex(number)
        if key not in headers:
            headers[key] = lens.header(rpc.call('eth_getBlockByNumber', [key, False]))
        lens.require(headers[key]['hash'].lower() == block_hash,
                     'Approval event is not in its canonical block')
    after = lens.header(rpc.call('eth_getBlockByNumber', [hex(end), False]))
    lens.require(after == block, 'end block changed during capture')
    result = {'schema': SCHEMA, 'source': endpoint, 'chain_id': 1, 'token': token,
              'token_address': lens.TOKENS[token], 'from_block': start, 'to_block': end,
              'end_block': block, 'logs': logs, 'log_headers': headers}
    validate_fill(result)
    return result


def join(before, after, fill):
    original = coverage.assess([before, after])
    missing = original['missing_intervals']
    lens.require(len(missing) == 1, 'expected exactly one missing interval')
    newly_seen = set(validate_fill(fill))
    gap = missing[0]
    lens.require(fill['from_block'] == gap['from_block']
                 and fill['to_block'] == gap['to_block'],
                 'backfill does not exactly cover the missing interval')
    lens.require(fill['chain_id'] == original['chain_id']
                 and fill['token'] == original['token']
                 and fill['token_address'] == original['token_address']
                 and original['owner_filter'] is None,
                 'backfill identity or owner filter differs')
    known = {(row['owner'], row['spender']) for row in original['discovered_pairs']}
    additions = sorted(newly_seen - known)
    union = sorted(known | newly_seen)
    lens.require(len(union) <= lens.MAX_PAIRS, 'more than 64 known pairs')
    # The two inherited observations have already been validated by Coverage Map.
    # The fill is event-only: its historical balances and allowances are unknown.
    return {
        'schema': 'approval-backfill-join-v1', 'status': 'event_window_closed',
        'chain_id': 1, 'token': original['token'],
        'token_address': original['token_address'],
        'target': original['target'], 'filled_interval': gap,
        'backfill_source': fill['source'], 'backfill_end_block_hash': fill['end_block']['hash'],
        'backfill_approval_logs': len(fill['logs']),
        'previously_known_pair_count': len(known),
        'newly_discovered_pairs': [{'owner': a, 'spender': b} for a, b in additions],
        'known_pair_count': len(union),
        'known_pairs_requiring_same_block_recheck':
            [{'owner': a, 'spender': b} for a, b in union],
        'recheck_required': True, 'complete_wallet_audit': False,
        'limitations': [
            'The backfill establishes the saved RPC claim of logs for this finite event interval only.',
            'Historical token balances and allowances were not read for the backfilled interval.',
            'Every known pair still needs a same-block allowance recheck before policy review.',
            'Earlier approvals, unknown spenders, Permit2 and signatures remain outside coverage.',
            'Public RPC logs and headers are trusted claims, not cryptographic Ethereum proofs.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', default=str(HERE.parent/'allowance-lens'/'observation.json'))
    parser.add_argument('--after', default=str(HERE.parent/'allowance-changes'/'lens-recheck.json'))
    parser.add_argument('--fill', default=str(HERE/'gap-events.json'))
    parser.add_argument('--capture', action='store_true', help='read public logs for the exact gap')
    parser.add_argument('--rpc', choices=ENDPOINTS, default=ENDPOINTS[0])
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args(argv)
    try:
        before, after = gate.load(args.before), gate.load(args.after)
        original = coverage.assess([before, after])
        lens.require(len(original['missing_intervals']) == 1,
                     'expected exactly one missing interval')
        if args.capture:
            lens.require(type(args.timeout) in (int, float) and math.isfinite(args.timeout)
                         and 0 < args.timeout <= 600, 'invalid timeout')
            target = lens.workspace_path(args.fill)
            lens.require(not target.exists() and not target.is_symlink(),
                         'backfill output must be a new workspace file')
            gap = original['missing_intervals'][0]
            fill = lens.run_bounded(capture,
                (args.rpc, original['token'], gap['from_block'], gap['to_block']),
                timeout=args.timeout)
            result = join(before, after, fill)
            encoded = json.dumps(fill, indent=2) + '\n'
            lens.require(len(encoded.encode()) <= MAX_BYTES, 'backfill exceeds 96 KiB')
            with target.open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        else:
            fill = gate.load(args.fill)
            result = join(before, after, fill)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
