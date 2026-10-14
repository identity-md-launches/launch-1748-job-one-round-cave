#!/usr/bin/env python3
"""Replay each newest piece and record bounded summaries; live reads are separate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    previous = json.loads(Path('gathering/latest-demos-20.json').read_text())
    commands = [(item['command'][2:], item['exit']) for item in previous]
    commands += [
        (['line-1/tools/zto-witness-packet/zto_witness_packet.py', '--demo'], 0),
        (['line-1/tools/zto-witness-packet/zto_witness_packet.py', '--packet',
          'line-1/tools/zto-witness-packet/live-packet.json', '--policy',
          'line-1/tools/zto-witness-packet/live-policy.json', '--minimum-distinct-groups', '2',
          '--expected-packet-sha256', '8bb4c8dcb864ffa5d32bed119e7dbfe52d30b6e6139f185ea0bfa2eaee5c1cfb'], 2),
        (['line-2/tools/approval-coverage/approval_coverage.py'], 0),
        (['line-2/tools/approval-backfill/approval_backfill.py'], 0),
        (['line-3/tools/code-frontier-checkpoint/demo.py'], 0),
        (['line-4/tools/gas-budget/gas_budget.py', 'demo'], 0),
        (['shared/proof-gas-budget/proof_gas_budget.py'], 0),
    ]
    results = []
    for args, expected in commands:
        done = subprocess.run([sys.executable, '-B'] + args, capture_output=True,
                              text=True, timeout=30)
        value = json.loads(done.stdout) if done.stdout else {}
        results.append({'command': ['python3', '-B'] + args, 'exit': done.returncode,
                        'expected_exit': expected, 'passed': done.returncode == expected,
                        'stdout_sha256': hashlib.sha256(done.stdout.encode()).hexdigest(),
                        'summary': {key: value[key] for key in ('status', 'verdict', 'decision',
                            'demonstration_passed', 'block', 'bound', 'reasons', 'counts',
                            'known_pair_count', 'backfill_approval_logs', 'recheck_required',
                            'required_by_policy_gas', 'estimate_gas', 'ZTO', 'IMD') if key in value},
                        'stderr': done.stderr})
    # Summaries retain selected structured context, not huge runtime dumps.
    raw = json.dumps({'all_passed': all(x['passed'] for x in results), 'checks': results}, indent=1)+'\n'
    assert len(raw.encode()) < 100_000
    Path('gathering/latest-demos-21.json').write_text(raw)
    print(json.dumps({'all_passed': all(x['passed'] for x in results), 'commands': len(results)}))
    return 0 if all(x['passed'] for x in results) else 1


if __name__ == '__main__':
    sys.exit(main())
