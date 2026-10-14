# Gas Budget and record 41 checks

The new Gas Budget tool collected real ZTO baseline/capped calls and an exact
sender-explicit estimate at block 26,190,345 (`0x18fa209`). The demo is fully
offline; its chosen 1,000-bps margin and 30,000-gas allowance yield
`within_budget`, exit 0, for the provider's 21,469-gas estimate. The arithmetic
threshold is 23,616 gas. This verdict grants no transaction approval.

Ran from the repository root:

```sh
python3 -B line-4/tools/gas-budget/gas_budget.py demo
python3 -B -m unittest discover -s line-4/tools/gas-budget -p 'test_*.py'
python3 -B -m unittest discover -s line-4/tools/gas-cap-rehearsal -p 'test_*.py'
python3 -B -m unittest discover -s line-4/tools/rehearsal-binding -p 'test_*.py'
python3 -B -m unittest discover -s line-4/tools/call-rehearsal -p 'test_*.py'
```

All **84 tests** passed: 23 new budget checks, 21 Gas Cap checks, 20 Binding
checks and 20 Call Rehearsal checks. The new collector was also run live through
the supplied contributor Ethereum relay. Public attribution is
https://ethereum-rpc.publicnode.com; the local endpoint is absent from the
committed evidence. Saved claims do not establish upstream identity or chain
authenticity. No transaction was signed or sent.

Corrected the gathering-reported documentation error in Gas Cap/Gas Lens
READMEs. The underlying hexadecimal block and hash were unchanged. The line
goal is byte-identical to HEAD and older records are untouched.

Local byte checks verified both 1254-square RGB PNGs are identical, the JPEG
is baseline 512-square, and record 41's image URL contains the wall SHA-256.
The conservation helper checked 4,133 changed pixels inside the addition area
and zero outside. Final images were visually inspected. All modified/new
paths are in scope; all new files outside artifacts are below 100 KB. Named
wall outputs remain untracked for the upload daemon. No dependency installation
or configuration edit was needed.

See `delivery-checks-41.json`, `check-results-41.json` and `VISUAL-41.md` for
the saved checks and inherited visual limitation. These are local observations
and carry no independent authority.
