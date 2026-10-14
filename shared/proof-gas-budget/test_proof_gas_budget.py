import copy
import unittest
import proof_gas_budget as tool


class RealEvidenceTests(unittest.TestCase):
    def setUp(self):
        read = tool.budget.binding.read_json
        self.proof = read('shared/proof-gas-cap/zto-proof.json')
        self.evidence = read('line-4/tools/gas-budget/zto-budget-evidence.json')
        self.policy = read('line-4/tools/gas-budget/zto-budget-policy.json')

    def check(self):
        return tool.evaluate(self.proof, self.evidence, self.policy)

    def test_real_join_and_input_immutability(self):
        before = copy.deepcopy((self.proof, self.evidence, self.policy))
        result = self.check()
        self.assertEqual(result['status'], 'historical_context_joined')
        self.assertEqual(result['gas_budget']['required_by_policy_gas'], '23616')
        self.assertEqual(int(result['joined_request']['block']['number'], 16), 26190345)
        self.assertFalse(result['transaction_approved'])
        self.assertIn('unresolved_calls', result['code_identity'])
        self.assertEqual(before, (self.proof, self.evidence, self.policy))

    def test_real_older_proof_cannot_join(self):
        self.proof = tool.budget.binding.read_json('line-3/tools/code-proof/zto-proof.json')
        result = self.check()
        self.assertEqual(result['reasons'], ['code-call-context-mismatch'])
        self.assertIsNone(result['joined_request'])

    def test_proof_tampering_refused(self):
        self.proof['observation']['nodes'][0]['code'] = '0x6000'
        with self.assertRaises(ValueError):
            self.check()

    def test_higher_margin_withholds_despite_matching_code(self):
        self.policy['minimum_headroom_bps'] = 10000
        result = self.check()
        self.assertTrue(result['context_aligned'])
        self.assertEqual(result['reasons'], ['gas-budget-over_budget'])
        self.assertIsNone(result['joined_request'])

    def test_provider_failure_never_joins(self):
        self.evidence['estimate']['outcome'] = {'error': {'code': -32000, 'message': 'synthetic test failure'}}
        result = self.check()
        self.assertEqual(result['reasons'], ['gas-budget-inconclusive'])
        self.assertIsNone(result['joined_request'])

    def test_estimate_caller_mismatch_withholds(self):
        self.evidence['estimate']['call']['from'] = self.policy['request']['call']['to']
        result = self.check()
        self.assertEqual(result['reasons'], ['gas-budget-mismatch'])
        self.assertIsNone(result['joined_request'])

    def test_changed_expected_bytes_withholds(self):
        self.policy['request']['expected_return'] = '0x'
        result = self.check()
        self.assertEqual(result['reasons'], ['gas-budget-mismatch'])

    def test_boolean_margin_refused(self):
        self.policy['minimum_headroom_bps'] = True
        with self.assertRaises(ValueError):
            self.check()


if __name__ == '__main__':
    unittest.main()
