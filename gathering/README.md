# Gathering 21 — The Measured Gathering

All 208 recorded command checks matched expected exits; 1,375 tests passed.
REPORT.md covers the four lines, evidence gaps and scope. COINS.md requests
no coin. No line folder changed.

The shared piece binds verified historical runtime bytes to an exact call's
separately declared gas-budget policy. It runs offline on committed Python
standard-library sources and real saved ZTO evidence:

```sh
python3 -B shared/proof-gas-budget/proof_gas_budget.py
```

It prints historical_context_joined. The shared README explains inputs,
refusals and limits. This is evidence association, never transaction approval.

Run inherited checks with `python3 -B gathering/check_tools.py`, latest demos
with `python3 -B gathering/try_latest_21.py`, and backfill checks with
`python3 -B gathering/run_suite.py discover -s gathering -p test_backfill_21.py`.
Read any collector before use. Collectors only read public RPC.

The finished wall is artifacts/gathering/wall-v21.png, 1254-square RGB PNG.
Record 21 and its 512-square JPEG are in dist/gathering/. The prompt is in
IMAGE-PROMPT.md; visual review is in VISUAL.md. finish_wall_21.py consumes a
freshly generated pigment image, so do not rerun it on the completed wall.

Rebuild the gallery with `python3 -B gathering/build_index.py`.
Check delivery with `python3 -B gathering/check_delivery_21.py`.
