"""Offline real ZTO-first/IMD-second checkpoint review, without invented trust."""
import json
from pathlib import Path
import code_frontier_checkpoint as tool

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


def main():
    chain = tool.read_json(TOOLS / 'code-ancestry/zto-ancestry.json')
    height = tool.lens.quantity(chain['checkpoint']['number'])
    results = {}
    for token in ('zto', 'imd'):
        source = tool.read_json(TOOLS / 'code-proof' / (token + '-proof.json'))
        review = tool.read_json(HERE / (token + '-example-review.json'))
        result = tool.evaluate(source, [], review, chain, height)
        results[token.upper()] = {
            'decision': result['decision'], 'reasons': result['reasons'],
            'code_block': result['code_block'], 'checkpoint': result['checkpoint'],
            'code_age_blocks': result['code_age_blocks'],
            'parent_links_verified_per_bundle': result['parent_links_verified_per_bundle'],
            'measured_runtime_count': len(result['measured_runtimes']),
            'missing_constant_targets': result['missing_constant_targets'],
            'unresolved_call_site_count': result['unresolved_call_site_count'],
            'caller_supplied_checkpoint_hash_matched': False,
            'code_evidence_refreshed': result['code_evidence_refreshed']}
    stale_review = tool.read_json(HERE / 'zto-example-review.json')
    stale_review['max_age_blocks'] = 7
    stale = tool.evaluate(tool.read_json(TOOLS / 'code-proof/zto-proof.json'),
                          [], stale_review, chain, height)
    results['stale_ZTO_reasons'] = stale['reasons']
    results['demonstration_passed'] = (
        results['ZTO']['reasons'] == ['missing-caller-checkpoint-anchor']
        and results['IMD']['reasons'] == ['missing-constant-target-proofs',
                                        'unresolved-call-operands',
                                        'missing-caller-checkpoint-anchor']
        and results['IMD']['unresolved_call_site_count'] == 11
        and results['IMD']['missing_constant_targets'] ==
        ['0x1a44076050125825900e736c501f859c50fe728c']
        and all(results[token]['code_age_blocks'] == 8
                and results[token]['parent_links_verified_per_bundle'] == 8
                and not results[token]['code_evidence_refreshed']
                for token in ('ZTO', 'IMD')))
    results['demonstration_passed'] &= stale['reasons'] == [
        'code-evidence-too-old', 'missing-caller-checkpoint-anchor']
    results['note'] = ('Historical real proof/header replay. Example review hashes are copied '
                       'from evidence, not independently audited approvals. No anchor supplied.')
    return results


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
