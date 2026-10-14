"""Policy boundaries, exact-context refusal and read-only collection checks."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import gas_budget as budget

HERE = Path(__file__).resolve().parent


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.evidence = budget.binding.read_json(HERE / 'zto-budget-evidence.json')
        self.policy = budget.binding.read_json(HERE / 'zto-budget-policy.json')

    def evaluate(self):
        return budget.evaluate(self.evidence, self.policy)

    def set_allowance(self, gas):
        # Adjust the independent reviewer input and the described paired experiment.
        # This is a synthetic boundary test, not a claim of new real observations.
        self.policy['request']['gas_limit'] = str(gas)
        self.evidence['cap_evidence']['request']['gas_limit'] = str(gas)

    def test_real_offline_evidence(self):
        with patch.object(budget.core.RPC, 'call', side_effect=AssertionError('network')):
            result = self.evaluate()
        self.assertEqual(result['verdict'], 'within_budget')
        self.assertEqual(result['estimate_gas'], '21469')
        self.assertEqual(result['required_by_policy_gas'], '23616')
        self.assertEqual(result['spare_above_policy_gas'], '6384')
        self.assertEqual(result['estimate']['transport'], 'contributor-relay')

    def test_exact_integer_ceiling(self):
        self.set_allowance(23616)
        self.assertEqual(self.evaluate()['verdict'], 'within_budget')
        self.set_allowance(23615)
        self.assertEqual(self.evaluate()['verdict'], 'over_budget')

    def test_zero_margin(self):
        self.policy['minimum_headroom_bps'] = 0
        self.set_allowance(21469)
        self.assertEqual(self.evaluate()['verdict'], 'within_budget')
        self.set_allowance(21468)
        result = self.evaluate()
        self.assertEqual(result['verdict'], 'over_budget')
        self.assertEqual(result['spare_above_estimate_gas'], '-1')

    def test_uint64_arithmetic_never_rounds_through_float(self):
        gas = 2**64 - 1
        self.evidence['estimate']['outcome'] = {'result': hex(gas)}
        self.set_allowance(gas)
        self.policy['minimum_headroom_bps'] = 1
        result = self.evaluate()
        self.assertEqual(result['required_by_policy_gas'], str((gas*10001+9999)//10000))
        self.assertEqual(result['verdict'], 'over_budget')

    def test_omitted_estimate_sender_refused(self):
        del self.evidence['estimate']['call']['from']
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_estimate_context_mismatch(self):
        original = copy.deepcopy(self.evidence)
        for field, value in [('from', budget.core.TOKENS['IMD']),
                             ('to', budget.core.TOKENS['IMD']),
                             ('data', '0x70a08231'), ('value', '0x1')]:
            with self.subTest(field=field):
                self.evidence = copy.deepcopy(original)
                self.evidence['estimate']['call'][field] = value
                result = self.evaluate()
                self.assertEqual(result['verdict'], 'mismatch')
                self.assertIn('call', result['estimate_context_differences'])
        self.evidence = copy.deepcopy(original)
        self.evidence['estimate']['block']['number'] = '0x18fa208'
        self.evidence['estimate']['recheck']['number'] = '0x18fa208'
        self.assertEqual(self.evaluate()['verdict'], 'mismatch')

    def test_cap_context_mismatch(self):
        self.policy['request']['call']['from'] = budget.core.TOKENS['IMD']
        self.assertEqual(self.evaluate()['verdict'], 'mismatch')

    def test_cap_return_mismatch_precedes_budget(self):
        self.evidence['cap_evidence']['capped'] = {'result': '0x'}
        self.assertEqual(self.evaluate()['verdict'], 'mismatch')

    def test_expected_false_bytes_are_not_semantic_success(self):
        raw = '0x' + '00'*32
        self.policy['request']['expected_return'] = raw
        self.evidence['cap_evidence']['request']['expected_return'] = raw
        self.evidence['cap_evidence']['baseline'] = {'result': raw}
        self.evidence['cap_evidence']['capped'] = {'result': raw}
        self.assertEqual(self.evaluate()['verdict'], 'within_budget')
        self.assertIn('ABI semantics', self.evaluate()['limits'])

    def test_rpc_errors_never_grant_budget(self):
        original = copy.deepcopy(self.evidence)
        error = {'error': {'code': -32000, 'message': 'historical state unavailable'}}
        for container, key in [('estimate', 'outcome'), ('cap_evidence', 'baseline'),
                               ('cap_evidence', 'capped')]:
            with self.subTest(key=key):
                self.evidence = copy.deepcopy(original)
                self.evidence[container][key] = error
                self.assertEqual(self.evaluate()['verdict'], 'inconclusive')

    def test_estimate_quantities_are_strict(self):
        for value in ['0x0', '0x01', hex(2**64), 21469, True, '21469']:
            with self.subTest(value=value):
                self.evidence['estimate']['outcome'] = {'result': value}
                with self.assertRaises(ValueError):
                    self.evaluate()

    def test_changed_header_refused(self):
        self.evidence['estimate']['recheck']['timestamp'] = '0x6acf62d8'
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_unknown_estimate_fields_refused(self):
        self.evidence['estimate']['call']['gas'] = '0x7530'
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_boolean_chain_refused(self):
        self.evidence['estimate']['chain_id'] = True
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_policy_margins_strict(self):
        for margin in [True, -1, 100001, '1000', 0.5, None]:
            with self.subTest(margin=margin):
                self.policy['minimum_headroom_bps'] = margin
                with self.assertRaises(ValueError):
                    self.evaluate()

    def test_unknown_policy_fields_refused(self):
        self.policy['gas_price'] = '1'
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_duplicate_nonfinite_and_size_refused(self):
        for raw in [b'{"schema":1,"schema":2}', b'{"margin":NaN}', b' '*95001]:
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(ValueError):
                    budget.binding.parse_json(raw)

    def test_outside_path_refused_before_read(self):
        with self.assertRaises(ValueError):
            budget.binding.read_json(Path.cwd().parent / 'outside-budget.json')

    def test_input_fingerprints_change_with_margin(self):
        first = self.evaluate()
        self.policy['minimum_headroom_bps'] = 1001
        second = self.evaluate()
        self.assertNotEqual(first['policy_sha256'], second['policy_sha256'])
        self.assertEqual(first['evidence_sha256'], second['evidence_sha256'])

    def test_collector_exact_pins_and_allowlist(self):
        calls = []
        block = self.policy['request']['block']
        raw = self.policy['request']['expected_return']

        class FakeRPC:
            endpoint = budget.core.ENDPOINTS[0]
            via_relay = True

            def call(self, method, params):
                calls.append((method, copy.deepcopy(params)))
                if method == 'eth_chainId':
                    return '0x1'
                if method == 'eth_getBlockByNumber':
                    return copy.deepcopy(block)
                if method == 'eth_getCode':
                    return '0x60'
                if method == 'eth_call':
                    return raw
                if method == 'eth_estimateGas':
                    return '0x53dd'
                raise AssertionError(method)

        observed = budget.capture(FakeRPC(), self.policy)
        self.assertEqual(budget.evaluate(observed, self.policy)['verdict'], 'within_budget')
        self.assertTrue(all(method in budget.BudgetRPC.METHODS for method, _ in calls))
        state_calls = [(method, params) for method, params in calls
                       if method in ('eth_getCode', 'eth_call', 'eth_estimateGas')]
        for method, params in state_calls:
            self.assertEqual(params[1], {'blockHash': block['hash'], 'requireCanonical': True})
        estimates = [params[0] for method, params in calls if method == 'eth_estimateGas']
        self.assertEqual(estimates, [self.policy['request']['call']])
        self.assertNotIn('gas', estimates[0])
        caps = [params[0]['gas'] for method, params in calls
                if method == 'eth_call' and 'gas' in params[0]]
        self.assertEqual(caps, ['0x7530'])

    def test_bad_policy_makes_no_rpc_call(self):
        self.policy['minimum_headroom_bps'] = True
        with patch.object(budget.BudgetRPC, 'call', side_effect=AssertionError('network')):
            with self.assertRaises(ValueError):
                budget.capture(None, self.policy)

    def test_cli_demo_and_errors(self):
        command = [sys.executable, '-B', str(HERE / 'gas_budget.py')]
        result = subprocess.run(command + ['demo'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['verdict'], 'within_budget')
        result = subprocess.run(command + ['check', 'missing-budget.json',
                                str(HERE / 'zto-budget-policy.json')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['verdict'], 'inconclusive')

    def test_all_verdict_exit_codes(self):
        for verdict, code in [('within_budget', 0), ('over_budget', 1),
                              ('mismatch', 1), ('inconclusive', 2)]:
            self.assertEqual(budget.exit_code({'verdict': verdict}), code)


if __name__ == '__main__':
    unittest.main()
