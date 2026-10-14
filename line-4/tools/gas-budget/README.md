# Gas Budget

Compare a reviewer-chosen Ethereum gas allowance and minimum headroom margin
with a provider estimate for the **exact same historical call**. First require
both provider-default and explicitly capped calls to return the expected bytes.
Python 3.9+ standard library only; no installation or network is needed for replay.

Run from the repository root:

```sh
python3 -B line-4/tools/gas-budget/gas_budget.py demo
```

Tried on 2026-10-14: the demo returned `within_budget`, exit 0. A new real
read-only collection rehearsed ZTO `totalSupply()` at Ethereum block
**26,190,345** (`0x18fa209`), hash
`0x63af72b9379fba0e92a775299a9708eadffdd12395b382b481ce7976567d361c`.
Both calls returned the exact expected bytes encoding **10^27** ZTO base units.
The estimate with the same explicit PoolManager sender was **21,469 gas**.
The example retains the ancestor's **30,000 gas** experiment and chooses an
illustrative reviewer margin of **1,000 basis points (10%)**. Integer ceiling
arithmetic requires **23,616 gas** under that policy, leaving **6,384 gas**
above the policy threshold. These settings demonstrate a policy comparison;
they are not a recommendation or a requester-owned wallet setting.

ZTO is the real token at `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`.
The explicitly declared simulation sender is the real Uniswap v4 PoolManager
at `0x000000000004444c5dc75cb358380d2e3de08a90`. A contract sender in a
simulation does not establish an available transaction origin. The public
source attribution is https://ethereum-rpc.publicnode.com, accessed through
the assignment's contributor relay; upstream identity and independence remain
unverified. Local transport addresses are never saved. Nothing was sent.

The earlier Gas Lens example omitted its sender, whereas Gas Cap specified
one. This tool refuses an omitted or different estimate sender rather than
joining those two old experiments. It binds chain, sender, target, calldata,
native value, and block number/hash/timestamp for the new estimate. The capped
experiment must separately match the entire reviewed request, including gas
allowance and expected bytes. All state reads use `blockHash` and
`requireCanonical: true`; both collection phases recheck the exact header.

For another explicitly reviewed policy and saved evidence:

```sh
python3 -B line-4/tools/gas-budget/gas_budget.py check evidence.json policy.json
```

`zto-budget-policy.json` gives the complete format: exactly
`schema: gas-budget-policy-v1`, `request` (a Gas Cap `gas-cap-request-v1`),
and `minimum_headroom_bps` (integer 0 through 100,000, never a boolean).
Choose your own margin explicitly; no margin is inferred from evidence. The
request includes explicit `from`, `to`, `data`, `value`, Ethereum `chain_id: 1`,
an exact block header, a positive decimal `gas_limit` below 2^64, and exact
`expected_return` bytes. See the adjacent Gas Cap README for all request fields.

The policy comparison is:

```text
required_by_policy_gas = ceil(estimate_gas * (10000 + minimum_headroom_bps) / 10000)
within_budget iff allowance_gas >= required_by_policy_gas
```

All arithmetic uses integers, including values near the uint64 boundary.
An arithmetic threshold beyond uint64 cannot be met by a supported allowance.
The report includes signed spare-gas quantities and input SHA-256 fingerprints.
Fingerprints identify content; they do not authenticate it.

| Verdict | Exit | Meaning |
| --- | ---: | --- |
| `within_budget` | 0 | Exact returned bytes/context matched, estimate supplied, chosen margin met. |
| `over_budget` | 1 | Matching calls and estimate; allowance below the chosen margin threshold. |
| `mismatch` | 1 | Different request/estimate context or unexpected return bytes. |
| `inconclusive` | 2 | Provider failure, malformed or insufficient inputs, or changed recheck header. |

Context/return mismatches take precedence over provider errors. A provider error
never grants a budget verdict. Exact ABI `false` bytes can match if explicitly
expected; no verdict establishes semantic success.

To collect paired calls and a new estimate using a reviewed policy:

```sh
python3 -B line-4/tools/gas-budget/gas_budget.py live line-4/tools/gas-budget/zto-budget-policy.json --save line-4/tools/gas-budget/my-evidence.json
```

Use `--rpc https://eth.drpc.org` for the other supported public source or
`--relay 'http://127.0.0.1:<port>/rpc/1'` for an explicitly supplied contributor
transport. On a contributor machine use its supplied relay. Historical state
may be unavailable; preserve failures rather than changing the reviewed pin.
Save accepts only a new path inside the workspace with an existing parent.
No environment proxies, redirects, wallets, keys, secrets, or environment
variables are read. Only `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode`,
`eth_call` and `eth_estimateGas` are allowlisted. Nothing is signed, submitted,
paid, posted or deployed.

Evidence schema `gas-budget-evidence-v1` contains exactly `schema`, unmodified
`cap_evidence` (Gas Cap's existing schema), and `estimate`. The estimate records
exactly `chain_id`, `source`, `transport`, explicit `call`, `block`, `outcome`
(one canonical positive hex `result` below 2^64, or an RPC `error`), and
`recheck`. Provenance for the estimate and capped experiment remains visible
separately; matching does not require or imply independent providers.
Files are bounded to 95 KB; duplicate keys, non-finite JSON, unknown fields,
invalid quantities and paths outside the workspace are refused.

All 23 focused offline tests passed, covering real replay, ceiling/exact
boundaries, zero margins, large integer arithmetic, missing/mismatched callers,
changed context, false return bytes, RPC failures, strict inputs, hash pinning,
CLI exits and refusal before network on invalid policies:

```sh
python3 -B -m unittest discover -s line-4/tools/gas-budget -p 'test_*.py' -v
```

Retain adjacent `gas-cap-rehearsal/`, `rehearsal-binding/` and `call-rehearsal/`
when moving this tool. Dependencies are ordinary committed Python files.
Provider estimates are neither gas consumed nor guaranteed future requirements.
Calls may inspect `gasleft()` and use provider-default omitted fee context.
This tool does not authenticate the chain, ABI or provider, simulate sequential
writes, check balances/authority, predict current execution, or choose a safe
transaction gas limit. Freshness is a separate review decision.
