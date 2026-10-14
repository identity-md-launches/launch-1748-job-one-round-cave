# Gas Lens

Measure the provider's gas estimate for the **same call** as a saved Ethereum
rehearsal at a hash-pinned finalized block. A worker can compare the measurement
with a gas limit they choose. Python 3.9+ standard library only; keep the
adjacent `call-changes/` folder, whose validated call collector this tool uses.

From the repository root, one offline command shows it working:

```sh
python3 -B line-4/tools/gas-lens/gas_lens.py demo
```

Tried on 2026-10-14: the demo replayed saved real ZTO `totalSupply()` evidence
from PublicNode at finalized block **26,190,345** (`0x18fa209`), hash
`0x63af72b9379fba0e92a775299a9708eadffdd12395b382b481ce7976567d361c`.
The provider returned `1000000000000000000000000000` raw ZTO units to
`eth_call` and estimated **21,469 gas** for that same call. dRPC independently
returned 21,469 for an ad hoc read at the same block, but the committed bundle
contains only PublicNode's response; the tool makes no two-provider claim.
The demonstration supplies **no guessed gas limit** and makes no claim about the
current block.

For a fresh read-only ZTO measurement:

```sh
python3 -B line-4/tools/gas-lens/gas_lens.py live --save line-4/tools/gas-lens/my-new-evidence.json
```

Use `--token IMD` for the other real token, or `--from-observation PATH` to repeat
the exact target, sender presence, calldata, native value and return type of a
saved Call Rehearsal observation. Use `--rpc https://eth.drpc.org` or
`--block 0x...` to select the other public provider or a specified finalized
height. A custom call's sender must be explicit in its source observation; this
tool invents no address. The tool checks mainnet and target code, performs
`eth_call`, asks `eth_estimateGas` with the **same call and block hash**, then
rechecks the header. Historical state may be unavailable later.

For an owner or reviewer chosen limit, add `--max-gas DECIMAL` to `live`, `demo`,
or `replay PATH`. The exact estimate counts as `within_limit`; an estimate above
the limit is `above_limit`. Without a limit, the verdict is `measured`. RPC
estimate failure or a false, reverted or malformed rehearsal is `inconclusive`.
Exit codes are 0 for measured/within, 1 for above, and 2 for inconclusive or
invalid input. The limit is input for a comparison, never inferred from the
saved result. A matching limit is **not transaction approval**.

The evidence bundle is bounded to 95 KB, validated on replay, and saved only at
a new workspace-contained path. Duplicate JSON keys, non-finite values, wrong
headers, malformed quantities and unknown fields are refused. The inherited
transport uses a dedicated User-Agent, disables environment proxy discovery and
redirects, and accepts only the four existing read methods plus
`eth_estimateGas`. It never calls `eth_sendRawTransaction` or a signing method.
No wallet, key, secret or environment variable is read; nothing is signed,
submitted, paid, posted or deployed.

The estimate is a provider claim about historical simulation, not actual gas
consumed or a guaranteed future requirement. The provider supplies unspecified
gas/fee context, and saved RPC claims are not authenticated. It does not prove
authorization, state effects, safety or inclusion. The optional gas limit is
reviewer supplied and may need room beyond an estimate; this tool does not set
that policy.

Nine focused offline checks passed, including exact-limit behavior, adverse
call outcomes, malformed evidence, and verification that capture pins both
operations to the same hash:

```sh
python3 -B -m unittest discover -s line-4/tools/gas-lens -p 'test_*.py' -v
```
