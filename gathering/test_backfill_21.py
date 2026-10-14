"""Gathering checks for the line's shipped real event-backfill evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('gathering_backfill',
    Path('line-2/tools/approval-backfill/approval_backfill.py').resolve())
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.before = tool.gate.load('line-2/tools/allowance-lens/observation.json')
        self.after = tool.gate.load('line-2/tools/allowance-changes/lens-recheck.json')
        self.fill = tool.gate.load('line-2/tools/approval-backfill/gap-events.json')

    def test_real_replay_preserves_unknown_allowances(self):
        old = copy.deepcopy((self.before, self.after, self.fill))
        result = tool.join(self.before, self.after, self.fill)
        self.assertEqual(result['known_pair_count'], 24)
        self.assertEqual(result['backfill_approval_logs'], 6)
        self.assertEqual(len(result['newly_discovered_pairs']), 5)
        self.assertTrue(result['recheck_required'])
        self.assertFalse(result['complete_wallet_audit'])
        self.assertEqual(len(result['known_pairs_requiring_same_block_recheck']), 24)
        self.assertEqual(old, (self.before, self.after, self.fill))

    def test_shortened_interval_refused(self):
        self.fill['from_block'] += 1
        with self.assertRaises(ValueError):
            tool.join(self.before, self.after, self.fill)

    def test_log_hash_tampering_refused(self):
        self.fill['logs'][0]['blockHash'] = self.after['block']['hash']
        with self.assertRaises(ValueError):
            tool.join(self.before, self.after, self.fill)

    def test_wrong_token_refused(self):
        self.fill['token'] = 'IMD'
        with self.assertRaises(ValueError):
            tool.join(self.before, self.after, self.fill)


if __name__ == '__main__':
    unittest.main()
