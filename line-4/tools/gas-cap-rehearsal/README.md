# Gas Cap Rehearsal

Check whether an exact historical Ethereum call returns explicitly expected
bytes with a worker-selected gas allowance. The tool uses Python's standard
library and never signs, broadcasts, pays or deploys. It reads only explicit
workspace files and read-only RPC methods, with its own User-Agent.

One command from the repository root shows it working without a network:

```sh
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py demo
```

Tried on 2026-10-14: `demo` returned `matched`, exit 0. The committed evidence
was collected from real ZTO `totalSupply()` at Ethereum block **26,190,345**
(`0x18fa209`), hash
`0x63af72b9379fba0e92a775299a9708eadffdd12395b382b481ce7976567d361c`.
Both a provider-default-gas call and a **30,000 gas** call returned the same
reviewed 32 bytes, encoding **10^27** token base units. Both state reads used
the exact block hash and `requireCanonical: true`; code was present and the
header was rechecked. Source attribution is
`https://ethereum-rpc.publicnode.com`, routed through the contributor's
provided relay. This attribution does not verify upstream identity or
independence. The simulation sender is the real Uniswap v4 PoolManager;
this does not make that contract an available transaction origin.

A second real pair at the same block with **21,000 gas** preserved the baseline
return, but the provider rejected the capped call with `intrinsic gas too low`.
It correctly returns `inconclusive`, exit 2, rather than granting a match:

```sh
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py check line-4/tools/gas-cap-rehearsal/zto-tight-evidence.json line-4/tools/gas-cap-rehearsal/zto-tight-request.json
```

To check another reviewed request offline:

```sh
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py check evidence.json request.json
```

To collect paired read-only observations through a public endpoint:

```sh
python3 -B line-4/tools/gas-cap-rehearsal/gas_cap.py live line-4/tools/gas-cap-rehearsal/zto-request.json --save line-4/tools/gas-cap-rehearsal/my-evidence.json
```

`--rpc` selects either of the two public endpoints in Call Rehearsal.
`--relay` accepts an explicitly provided contributor transport; its address
is never written to evidence. The save destination must be a new file under
the workspace, with an existing parent. Existing evidence is never overwritten.

`request.json` has exactly these fields (see the committed ZTO request):

| Field | Required value |
| --- | --- |
| `schema` | `gas-cap-request-v1` |
| `chain_id` | Integer `1` |
| `call` | Exactly explicit `from`, `to`, even hexadecimal `data`, RPC-quantity `value` |
| `block` | Exactly RPC-quantity `number`, 32-byte `hash`, RPC-quantity `timestamp` |
| `gas_limit` | Canonical decimal string, 1 through 2^64−1 |
| `expected_return` | Exact even hexadecimal bytes, including `0x` for an empty return |

The capped call adds only `gas`; the baseline omits it. Both calls run
independently at the same historical state. Gas allowance, call, block and
expected return must all match the separate request when evidence is checked.
Unknown fields, duplicate JSON keys, non-finite numbers, oversized inputs,
implicit callers, wrong chains and outside-workspace paths are refused.

| Verdict | Exit | Meaning |
| --- | ---: | --- |
| `matched` | 0 | Both reported results equal the exact expected bytes. |
| `request_mismatch` | 1 | Evidence describes a different request. |
| `return_mismatch` | 1 | At least one returned result differs from expected bytes. |
| `inconclusive` | 2 | A provider call failed, or an input/transport check failed. |

This complements Gas Lens: it actually calls with a fixed allowance instead
of comparing an estimate to a limit. It measures neither consumed gas nor
minimum gas, and recommends no transaction gas limit. A contract can branch
on `gasleft()`; a low allowance can cause many kinds of error, and an RPC
message alone does not prove their cause. Exact ABI `false` bytes can match
if explicitly requested; `matched` does not claim semantic success. Provider
defaults still determine omitted fee context. No ABI authenticity, state
effects, current state, future execution, authorization, or provider/chain
authenticity is established. Saved evidence and content digests are claims
and identifiers, not proofs. Nothing is sent.

All **21 focused offline tests** passed, including both saved real pairs,
exact hash pinning, changed-header rejection, mismatched callers/calldata/
value/gas/expectations, malformed input, error handling and empty-code refusal:

```sh
python3 -B -m unittest discover -s line-4/tools/gas-cap-rehearsal -p 'test_*.py' -v
```

Dependencies are ordinary committed Python files in adjacent
`rehearsal-binding/` and `call-rehearsal/`; no package installation is required.
