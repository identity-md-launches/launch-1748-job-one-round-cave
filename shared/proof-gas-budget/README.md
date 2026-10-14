# Proof and Gas Budget Context

Recompute Line 3's runtime inclusion proof and Line 4's gas-budget comparison
from raw saved inputs. Join them only when Ethereum chain, contract, block
height and hash agree and the exact-call gas policy returns `within_budget`.
It prints both full reports, including unresolved dependencies and provenance.

From the repository root, with no network or installation:

```sh
python3 -B shared/proof-gas-budget/proof_gas_budget.py
```

Tried on 2026-10-14: real ZTO evidence at block 26,190,345 returned
`historical_context_joined`, exit 0. The separately declared illustrative policy
uses 30,000 gas and a 10% margin; the exact-sender estimate is 21,469 gas,
requiring 23,616 gas under that policy. The saved proof was collected by
Gathering 20 through dRPC; Line 4 attributes its calls to PublicNode through a
contributor relay. No fresh chain read or authenticated provider is claimed.

Use `--proof`, `--evidence` and `--policy` to supply your own workspace files.
The policy is separately supplied, never extracted from a proof or estimate.
Defaults are historical demonstrations, not a recommendation. Each input is
at most 95 KB; duplicate JSON keys, non-finite values and outside-workspace
paths are refused by the inherited reader. Exit 0 means joined evidence,
2 means withheld, and 1 means invalid input (argument errors exit 2).

Eight tests cover the real join, older proof refusal, code corruption, margin
refusal, provider failure, caller/return mismatch and strict margin types:

```sh
python3 -B -m unittest discover -s shared/proof-gas-budget -p 'test_*.py'
```

Keep the repository's ordinary committed `line-3/tools/`, `line-4/tools/`,
`shared/evidence-alignment/` and `shared/proof-gas-cap/zto-proof.json` with this
tool. Python standard library only. Nothing is installed, written, signed,
sent, paid, posted or deployed; no wallet, key, secret or environment is read.

This is evidence association, never transaction approval. Proofs bind runtime
to the supplied header, whose consensus authenticity remains unverified.
Call returns and estimates remain provider claims. A chosen margin proves
neither consumed gas nor a safe future gas limit. Code semantics, complete
dependencies, sender authority, balances and future execution remain unknown.
