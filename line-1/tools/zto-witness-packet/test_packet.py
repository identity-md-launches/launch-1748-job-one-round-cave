import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import zto_witness_packet as tool


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.policy = tool.demo_inputs()

    def synthetic_pair(self):
        # Policy plumbing only: relabeled real data is NOT independent RPC evidence.
        labels = ('https://one.example/rpc', 'https://two.example/rpc')
        for capture, label in zip(self.packet['captures'], labels):
            capture['snapshot']['base']['source'] = capture['quoter']['source'] = label
        self.policy['sources'] = dict(zip(labels, ('one', 'two')))

    def test_real_single_source_packet_withholds_offline(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = tool.demo()
        self.assertFalse(result['bound_released'])
        self.assertIsNone(result['bound'])
        self.assertIn('duplicate_source_label', result['reasons'])
        self.assertTrue(result['receiver_fingerprint_checked'])

    def test_synthetic_pair_replays_and_floors(self):
        self.synthetic_pair()
        result = tool.review(self.packet, self.policy, 2)
        self.assertTrue(result['bound_released'])
        self.assertEqual(result['bound']['planning_minimum_raw'], '15139234039518')
        output = int(result['bound']['estimated_output_raw'])
        self.assertEqual(int(result['bound']['planning_minimum_raw']), output * 9900 // 10000)
        self.assertEqual(len(result['captures_sha256']), 2)

    def test_receiver_controls_override_sender(self):
        self.synthetic_pair()
        self.policy['sources'] = {label: 'one' for label in self.policy['sources']}
        result = tool.review(self.packet, self.policy, 2)
        self.assertFalse(result['bound_released'])
        self.assertIn('insufficient_distinct_receiver_provider_groups', result['reasons'])

    def test_sender_cannot_embed_policy_or_report(self):
        for key in ('policy', 'bound', 'quorum_report'):
            packet = copy.deepcopy(self.packet)
            packet[key] = self.policy
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.review(packet, self.policy, 2)

    def test_fingerprint_tracks_evidence_not_formatting(self):
        self.synthetic_pair()
        expected = tool.replay.digest(self.packet)
        reformatted = json.loads(json.dumps(self.packet, indent=4))
        self.assertTrue(tool.review(reformatted, self.policy, 2, expected)['bound_released'])
        reformatted['captures'][0]['snapshot']['base']['source'] = 'https://changed.example/rpc'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            tool.review(reformatted, self.policy, 2, expected)

    def test_false_fingerprint_refused_before_arithmetic(self):
        with patch.object(tool.quorum, 'evaluate', side_effect=AssertionError('must not evaluate')):
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                tool.review(self.packet, self.policy, 2, 'f' * 64)
        for value in (True, 'F' * 64, 'x', 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tool.review(self.packet, self.policy, 2, value)

    def test_raw_quoter_tampering_refused(self):
        self.synthetic_pair()
        self.packet['captures'][1]['quoter']['results'][0]['raw_result'] = '0x' + '0' * 128
        with self.assertRaisesRegex(ValueError, 'flags'):
            tool.review(self.packet, self.policy, 2)

    def test_calldata_amount_binding(self):
        self.synthetic_pair()
        self.packet['amount'] = '2'
        with self.assertRaisesRegex(ValueError, 'candidate mismatch'):
            tool.review(self.packet, self.policy, 2)

    def test_direction_is_never_reinterpreted(self):
        self.policy['input_token'] = 'IMD'
        with self.assertRaisesRegex(ValueError, 'direction'):
            tool.review(self.packet, self.policy, 2)

    def test_receiver_ceiling_and_age_withhold(self):
        self.synthetic_pair()
        for field, value, reason in (
            ('maximum_input_raw', '1', 'input_exceeds_receiver_ceiling'),
            ('maximum_slippage_bps', 0, 'slippage_exceeds_receiver_ceiling'),
            ('reference_block', self.policy['reference_block'] + 1, 'outside_caller_age_limit'),
        ):
            policy = dict(self.policy, **{field: value})
            with self.subTest(field=field):
                result = tool.review(self.packet, policy, 2)
                self.assertFalse(result['bound_released'])
                self.assertIn(reason, result['reasons'])

    def test_strict_shapes_and_types(self):
        for field, value in (('captures', []), ('captures', self.packet['captures'] * 5),
                             ('amount', True), ('amount', '1e18'), ('input_token', 'ETH'),
                             ('slippage_bps', True), ('slippage_bps', 10000)):
            packet = dict(self.packet, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.validate_packet(packet)
        packet = copy.deepcopy(self.packet)
        packet['captures'][0]['snapshot'] = 'https://untrusted.example/data'
        with self.assertRaisesRegex(ValueError, 'inline'):
            tool.validate_packet(packet)
        for minimum in (True, 1, 9, 3):
            with self.subTest(minimum=minimum), self.assertRaises(ValueError):
                tool.review(self.packet, self.policy, minimum)

    def test_review_opens_no_files(self):
        self.synthetic_pair()
        with patch.object(Path, 'open', side_effect=AssertionError('inline review must not open files')):
            self.assertTrue(tool.review(self.packet, self.policy, 2)['bound_released'])

    def test_pack_reads_once_and_does_not_mutate(self):
        request, observation, check = tool.quorum.demo_request()
        originals = copy.deepcopy((request, observation, check))
        sequence = iter((observation, check, observation, check))
        calls = []
        def loader(ref):
            calls.append(ref)
            return next(sequence)
        packet = tool.pack(request, loader)
        self.assertEqual(len(calls), 4)
        self.assertEqual((request, observation, check), originals)
        observation['base']['source'] = 'https://changed.example/rpc'
        self.assertNotEqual(packet['captures'][0]['snapshot']['base']['source'], observation['base']['source'])

    def test_oversized_packet_refused(self):
        self.packet['captures'][0]['snapshot']['padding'] = 'x' * tool.MAX_BYTES
        with self.assertRaisesRegex(ValueError, '100 KB'):
            tool.validate_packet(self.packet)

    def test_strict_json_reader_and_cli_roundtrip(self):
        scratch = Path('test/scratch'); scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='packet-', dir=scratch) as name:
            directory = Path(name)
            bad = directory / 'bad.json'
            for text in ('{"schema":1,"schema":2}', '{"n":1.5}', '{"n":NaN}'):
                bad.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    tool.replay.read_json(str(bad))
            request, observation, check = tool.quorum.demo_request()
            snapshot_path, quoter_path = directory / 'snapshot.json', directory / 'quoter.json'
            snapshot_path.write_text(json.dumps(observation)); quoter_path.write_text(json.dumps(check))
            request['candidates'] = [{'snapshot': str(snapshot_path), 'quoter': str(quoter_path)}] * 2
            request_path, policy_path = directory / 'request.json', directory / 'policy.json'
            request_path.write_text(json.dumps(request)); policy_path.write_text(json.dumps(self.policy))
            script = str(Path(tool.__file__).resolve())
            produced = subprocess.run([sys.executable, '-B', script, '--pack', str(request_path)],
                                      capture_output=True, text=True)
            self.assertEqual(produced.returncode, 0, produced.stderr)
            packet_path = directory / 'packet.json'; packet_path.write_text(produced.stdout)
            received = subprocess.run([sys.executable, '-B', script, '--packet', str(packet_path),
                                       '--policy', str(policy_path), '--minimum-distinct-groups', '2'],
                                      capture_output=True, text=True)
            self.assertEqual(received.returncode, 2, received.stderr)
            result = json.loads(received.stdout)
            self.assertEqual(result['packet_sha256'], tool.replay.digest(json.loads(produced.stdout)))
            self.assertFalse(result['bound_released'])


if __name__ == '__main__':
    unittest.main()
