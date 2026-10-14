#!/usr/bin/env python3
"""Review historical runtime dependencies through a later execution checkpoint."""
import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-frontier-review'))
import code_frontier_review as review_tool

ancestry = review_tool.frontier.targets.calls.ancestry
lens = review_tool.lens
require = lens.require


def reject_constant(value):
    raise ValueError('non-finite JSON number: ' + value)


def read_json(filename):
    """Read only an explicit bounded workspace file, without following escapes."""
    path = Path(filename).resolve()
    require(path.is_relative_to(Path.cwd().resolve()), 'input must be inside workspace')
    with path.open('rb') as stream:
        raw = stream.read(lens.MAX_RESPONSE + 1)
    require(len(raw) <= lens.MAX_RESPONSE, 'input exceeds 100000 bytes')
    return json.loads(raw, object_pairs_hook=ancestry.no_duplicates,
                      parse_constant=reject_constant)


def evaluate(source, target_proofs, review, chain, as_of_block,
             checkpoint_hash=None):
    """Never substitute an observed code-block hash for the caller's checkpoint."""
    require(isinstance(target_proofs, list) and len(target_proofs) <= 16,
            'at most 16 additional proof bundles')
    require(type(as_of_block) is int and 0 <= as_of_block < 2**64,
            'as_of_block must be a uint64 integer')
    # Reconstruct every parent link and every raw account/runtime/storage proof.
    # One shared ancestry interval must start at each bundle's exact block.
    linked = [ancestry.verify(bundle, chain, checkpoint_hash)
              for bundle in [source, *target_proofs]]
    checkpoint = linked[0]['checkpoint']
    require(as_of_block >= lens.quantity(checkpoint['number']),
            'as_of_block precedes evidence checkpoint')
    require(all(row['checkpoint'] == checkpoint
                and row['code_block'] == linked[0]['code_block']
                for row in linked), 'conflicting checkpoint context')

    # The ancestor applies every identity, age and open-frontier requirement.
    # Its direct code-block anchor is deliberately absent: only checked parent
    # linkage can discharge that requirement here. No other refusal is removed.
    result = review_tool.evaluate(source, target_proofs, review, as_of_block)
    require('missing-caller-anchor' in result['reasons'],
            'ancestor did not preserve its direct-anchor requirement')
    reasons = [reason for reason in result['reasons']
               if reason != 'missing-caller-anchor']
    if checkpoint_hash is None:
        reasons.append('missing-caller-checkpoint-anchor')
    result = dict(result)
    result.pop('caller_supplied_anchor_hash_matched')
    result.update({
        'schema': 'code-frontier-checkpoint-result-v1',
        'decision': 'refuse' if reasons else 'accept-bounded-code-identities',
        'reasons': reasons,
        'checkpoint': checkpoint,
        'anchor_kind': ('caller-supplied-execution-checkpoint' if checkpoint_hash is not None
                        else 'unanchored-rpc-checkpoint'),
        'caller_supplied_checkpoint_hash_matched': checkpoint_hash is not None,
        'parent_links_verified_per_bundle': linked[0]['parent_links_verified'],
        'proof_bundle_count': len(linked),
        'linked_proof_roots': sorted(row['target'] for row in linked),
        'ancestry_provenance': linked[0]['ancestry_provenance'],
        'proof_provenance': [{'target': row['target'], 'provenance': row['proof_provenance']}
                             for row in sorted(linked, key=lambda row: row['target'])],
        'code_evidence_refreshed': False,
        'code_at_checkpoint_verified': False,
        'continuous_stability_verified': False,
        'consensus_verified': False,
        'scope': 'Raw historical runtime/state proofs and exact reviewed identities in a '
                 'bounded dependency scan, linked by every intervening execution header to '
                 'a later checkpoint. Age is measured from the original code block, never '
                 'the checkpoint. Caller must independently trust review, checkpoint hash '
                 'and reference height. Hash equality does not authenticate a checkpoint. '
                 'No complete dependencies, routing, reachability, consensus/finality, '
                 'continuous stability, later/current code, safety or transaction authority '
                 'is established.'})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='workspace raw Code Proof JSON')
    parser.add_argument('--target-proof', action='append', default=[],
                        help='same-block raw proof of a discovered constant call target')
    parser.add_argument('--review', required=True, help='independently selected exact runtime list')
    parser.add_argument('--ancestry', required=True, help='1 to 32 consecutive descendant headers')
    parser.add_argument('--as-of-block', type=int, required=True, help='decimal reference height')
    parser.add_argument('--checkpoint-hash', help='separately trusted execution checkpoint hash')
    args = parser.parse_args(argv)
    try:
        require(len(args.target_proof) <= 16, 'too many target proofs')
        result = evaluate(read_json(args.source),
                          [read_json(path) for path in args.target_proof],
                          read_json(args.review), read_json(args.ancestry),
                          args.as_of_block, args.checkpoint_hash)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['decision'] == 'accept-bounded-code-identities' else 3
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Frontier Checkpoint: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
