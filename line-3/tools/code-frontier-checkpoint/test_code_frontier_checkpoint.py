"""Real proof replay and adversarial checkpoints; synthetic descendants are tests only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import code_frontier_checkpoint as tool

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


def read(path):
    return tool.read_json(TOOLS / path)


def test_descendants(bundle, count=2):
    """Invent linked headers in memory to test logic, never real-chain evidence."""
    proof = tool.ancestry.proof
    current, fields = tool.ancestry.header_identity(bundle['header_rlp'])
    headers = []
    for _ in range(count):
        fields[0] = bytes.fromhex(current['hash'][2:])
        fields[8] = proof.integer_bytes(tool.lens.quantity(current['number']) + 1)
        fields[11] = proof.integer_bytes(proof.scalar(fields[11]) + 12)
        encoded = '0x' + proof.rlp_encode(fields).hex()
        headers.append(encoded)
        current, _ = tool.ancestry.header_identity(encoded)
    return {'schema': 'code-ancestry-v1', 'chain_id': 1,
            'start': copy.deepcopy(bundle['observation']['block']),
            'checkpoint': current, 'headers': headers,
            'provenance': copy.deepcopy(read('code-ancestry/zto-ancestry.json')['provenance'])}


class CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zto = read('code-proof/zto-proof.json')
        cls.imd = read('code-proof/imd-proof.json')
        cls.chain = read('code-ancestry/zto-ancestry.json')
        cls.review = tool.read_json(HERE / 'zto-example-review.json')
        cls.height = 26185288

    def run_review(self, **changes):
        values = dict(source=self.zto, target_proofs=[], review=self.review,
                      chain=self.chain, as_of_block=self.height)
        values.update(changes)
        return tool.evaluate(**values)

    def test_real_zto_replayed_but_unanchored(self):
        result = self.run_review()
        self.assertEqual(result['reasons'], ['missing-caller-checkpoint-anchor'])
        self.assertEqual(result['parent_links_verified_per_bundle'], 8)
        self.assertEqual(result['code_age_blocks'], 8)
        self.assertEqual(result['linked_proof_roots'], [tool.lens.ZTO])
        self.assertTrue(result['raw_proofs_reverified'])
        self.assertFalse(result['caller_supplied_checkpoint_hash_matched'])
        self.assertNotIn('caller_supplied_anchor_hash_matched', result)

    def test_observed_checkpoint_exercises_hash_equality_only(self):
        # A copied observed hash tests matching logic, never independent trust.
        result = self.run_review(checkpoint_hash=self.chain['checkpoint']['hash'])
        self.assertEqual(result['decision'], 'accept-bounded-code-identities')
        self.assertTrue(result['caller_supplied_checkpoint_hash_matched'])
        for key in ('anchor_authenticity_verified', 'consensus_verified',
                    'continuous_stability_verified', 'code_at_checkpoint_verified',
                    'code_evidence_refreshed', 'dependency_completeness_verified',
                    'semantic_safety_verified', 'reachability_verified'):
            self.assertFalse(result[key], key)

    def test_age_boundary_uses_original_evidence_block(self):
        review = copy.deepcopy(self.review)
        review['max_age_blocks'] = 7
        result = self.run_review(review=review, checkpoint_hash=self.chain['checkpoint']['hash'])
        self.assertEqual(result['reasons'], ['code-evidence-too-old'])
        result = self.run_review(as_of_block=self.height + 1)
        self.assertEqual(result['code_age_blocks'], 9)
        self.assertIn('code-evidence-too-old', result['reasons'])

    def test_reference_cannot_precede_checkpoint_or_be_boolean(self):
        for height in (self.height - 1, True, -1, 1.0, '26185288', 2**64):
            with self.subTest(height=height), self.assertRaises(ValueError):
                self.run_review(as_of_block=height)

    def test_code_block_hash_cannot_substitute_for_later_checkpoint(self):
        with self.assertRaisesRegex(ValueError, 'checkpoint hash'):
            self.run_review(checkpoint_hash=self.zto['observation']['block']['hash'])

    def test_checkpoint_and_parent_tampering_fail_even_after_rehashing(self):
        proof = tool.ancestry.proof
        chain = test_descendants(self.zto, 1)
        _, fields = tool.ancestry.header_identity(chain['headers'][0])
        fields[0] = proof.keccak256(b'test-only wrong parent')
        chain['headers'][0] = '0x' + proof.rlp_encode(fields).hex()
        chain['checkpoint'], _ = tool.ancestry.header_identity(chain['headers'][0])
        with self.assertRaisesRegex(ValueError, 'parent hash'):
            self.run_review(chain=chain, checkpoint_hash=chain['checkpoint']['hash'])
        with self.assertRaises(ValueError):
            self.run_review(checkpoint_hash=tool.lens.digest(b'test-only wrong checkpoint'))

    def test_missing_reordered_and_repeated_headers_fail(self):
        for headers in (self.chain['headers'][:-1], list(reversed(self.chain['headers'])),
                        [self.chain['headers'][0]] * 8):
            chain = copy.deepcopy(self.chain)
            chain['headers'] = headers
            with self.subTest(count=len(headers)), self.assertRaises(ValueError):
                self.run_review(chain=chain)

    def test_trust_cannot_be_embedded_in_ancestry_or_review(self):
        for key in ('trusted', 'allow_unanchored', 'checkpoint_hash'):
            chain = copy.deepcopy(self.chain)
            chain[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_review(chain=chain)
            review = copy.deepcopy(self.review)
            review[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_review(review=review)

    def test_raw_proof_rechecked_and_saved_verdict_not_accepted(self):
        corrupt = copy.deepcopy(self.zto)
        corrupt['proofs'][0]['accountProof'].pop()
        with self.assertRaises(ValueError):
            self.run_review(source=corrupt)
        with self.assertRaises((ValueError, KeyError)):
            self.run_review(source=self.run_review())

    def test_forged_runtime_with_consistent_auxiliary_hashes_fails(self):
        corrupt = copy.deepcopy(self.zto)
        node = corrupt['observation']['nodes'][0]
        node.update(code='0x6000', code_bytes=2, code_hash=tool.lens.digest(b'\x60\x00'))
        corrupt['observation']['effective_code_hash'] = node['code_hash']
        corrupt['proofs'][0]['codeHash'] = node['code_hash']
        with self.assertRaisesRegex(ValueError, 'proven code hash'):
            self.run_review(source=corrupt)

    def test_real_imd_keeps_missing_target_and_unknown_sites(self):
        result = self.run_review(source=self.imd,
                                 review=tool.read_json(HERE / 'imd-example-review.json'),
                                 checkpoint_hash=self.chain['checkpoint']['hash'])
        self.assertEqual(result['reasons'], ['missing-constant-target-proofs',
                                            'unresolved-call-operands'])
        self.assertEqual(result['unresolved_call_site_count'], 11)
        self.assertEqual(len(result['unresolved_calls'][0]['sites']), 11)
        self.assertEqual(result['missing_constant_targets'],
                         ['0x1a44076050125825900e736c501f859c50fe728c'])

    def test_all_discovered_proofs_linked_with_unknowns_preserved(self):
        # The raw runtimes are real. Only these two descendant headers are synthetic.
        source = read('code-routes/imd-proof.json')
        target = read('code-target-proofs/imd-target-proof.json')
        review = read('code-frontier-review/imd-example-review.json')
        review['max_age_blocks'] = 2
        chain = test_descendants(source)
        result = tool.evaluate(source, [target], review, chain, 26188211,
                               chain['checkpoint']['hash'])
        self.assertEqual(result['proof_bundle_count'], 2)
        self.assertEqual(result['parent_links_verified_per_bundle'], 2)
        self.assertEqual(result['linked_proof_roots'],
                         sorted([tool.lens.IMD, target['observation']['target']]))
        self.assertEqual(result['missing_constant_targets'], [])
        self.assertEqual(result['unresolved_call_site_count'], 34)
        self.assertEqual(result['reasons'], ['unresolved-call-operands'])
        corrupt = copy.deepcopy(target)
        corrupt['proofs'][0]['accountProof'].pop()
        with self.assertRaises(ValueError):
            tool.evaluate(source, [corrupt], review, chain, 26188211)

    def test_different_block_unrelated_duplicate_and_excess_proofs_refused(self):
        for targets in ([read('code-routes/imd-proof.json')], [self.imd],
                        [self.zto], [self.zto] * 17):
            with self.subTest(count=len(targets)), self.assertRaises(ValueError):
                self.run_review(target_proofs=targets)

    def test_review_identity_requirements_survive_checkpoint_matching(self):
        review = copy.deepcopy(self.review)
        review['runtimes'][0]['code_hash'] = tool.lens.digest(b'test-only differing reviewed code')
        result = self.run_review(review=review, checkpoint_hash=self.chain['checkpoint']['hash'])
        self.assertEqual(result['reasons'], ['reviewed-runtime-set-or-hash-mismatch'])
        self.assertEqual(len(result['mismatched_runtime_hashes']), 1)

    def test_input_not_mutated_and_checkpoint_case_normalized(self):
        originals = copy.deepcopy((self.zto, self.review, self.chain))
        result = self.run_review(checkpoint_hash='0x' + self.chain['checkpoint']['hash'][2:].upper())
        self.assertEqual(result['checkpoint'], self.chain['checkpoint'])
        self.assertEqual((self.zto, self.review, self.chain), originals)

    def test_reader_refuses_duplicate_nonfinite_oversized_and_escape(self):
        scratch = Path.cwd() / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / 'input.json'
            for raw in ('{"schema":1,"schema":2}', '{"x":NaN}', '{"x":Infinity}',
                        ' ' * 100001):
                path.write_text(raw)
                with self.subTest(raw=raw[:25]), self.assertRaises(ValueError):
                    tool.read_json(path)
            path.unlink()
            path.symlink_to(Path.cwd().parent / 'must-not-be-read')
            with self.assertRaisesRegex(ValueError, 'inside workspace'):
                tool.read_json(path)

    def test_cli_exit_contract_and_empty_stdout_on_error(self):
        command = [sys.executable, '-B', str(HERE / 'code_frontier_checkpoint.py'),
                   '--source', str(TOOLS / 'code-proof/zto-proof.json'),
                   '--review', str(HERE / 'zto-example-review.json'),
                   '--ancestry', str(TOOLS / 'code-ancestry/zto-ancestry.json'),
                   '--as-of-block', str(self.height)]
        for extra, expected in (([], 3), (['--checkpoint-hash', self.chain['checkpoint']['hash']], 0),
                                (['--checkpoint-hash', self.zto['observation']['block']['hash']], 1)):
            process = subprocess.run(command + extra, capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, expected, process.stderr)
            if expected == 1:
                self.assertEqual(process.stdout, '')
                self.assertIn('checkpoint hash', process.stderr)
            else:
                self.assertTrue(json.loads(process.stdout)['raw_proofs_reverified'])
                self.assertEqual(process.stderr, '')
        process = subprocess.run(command[:3], capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, '')

    def test_demo_replays_real_evidence_without_anchor(self):
        spec = importlib.util.spec_from_file_location('checkpoint_demo', HERE / 'demo.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.main()['demonstration_passed'])


if __name__ == '__main__':
    unittest.main()
