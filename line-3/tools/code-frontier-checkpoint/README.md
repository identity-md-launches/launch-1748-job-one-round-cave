# Code Frontier Checkpoint

Review historical Ethereum executable code and its supplied constant-call dependencies against a **later execution checkpoint**. A worker who independently trusts a newer block hash can verify every intervening parent link instead of needing a separate trusted hash for the original code block. Every raw account, runtime, storage and header proof is rechecked. Every existing identity, age, missing-target and unresolved-call requirement from Code Frontier Review remains in force.

Run one command from the repository root, offline, using Python 3.9+ and only the standard library:

```sh
python3 -B line-3/tools/code-frontier-checkpoint/demo.py
```

**What happened when tried:** `demonstration_passed` was `true`. Saved real ZTO proofs were checked first, then IMD, at Ethereum block **26,185,280**. Eight saved real descendant headers linked them to checkpoint **26,185,288**. ZTO matched its example reviewed identity but refused for `missing-caller-checkpoint-anchor`. IMD also retained one missing constant-target proof and **11 unresolved call operands**. Tightening ZTO's example age limit to seven blocks refused it as too old even though the checkpoint was only just reached. The full demo output is saved in `demo-result.json`.

The example review lists copy the historical runtime hashes for demonstration; they are not independent audits or approvals. Their eight-block age limit is an example, not a recommended policy. No independent checkpoint anchor is supplied or invented by the demo. All chain evidence is inherited real historical evidence; no fresh chain observation is claimed.

For an explicit unanchored replay, this command prints a structured refusal and exits **3**:

```sh
python3 -B line-3/tools/code-frontier-checkpoint/code_frontier_checkpoint.py --source line-3/tools/code-proof/zto-proof.json --review line-3/tools/code-frontier-checkpoint/zto-example-review.json --ancestry line-3/tools/code-ancestry/zto-ancestry.json --as-of-block 26185288
```

For your own evidence, supply `--source` as a raw Code Proof bundle, `--review` as an independently selected Code Frontier Review document, `--ancestry` as a Code Ancestry document, and `--as-of-block` as your explicit decimal reference height. Repeat `--target-proof` for up to sixteen discovered constant-target raw proofs. Every bundle must belong to the exact original block, including its hash, and must join the same ancestry interval. Duplicate, unrelated, corrupt or wrong-block proofs fail. The ancestry must contain **1–32** consecutive descendant headers; no header is skipped and no future block is awaited. This tool does not collect data or make network requests. The ancestor Code Ancestry collector can prepare an interval of already-existing headers separately.

Supply `--checkpoint-hash` only from your independently trusted execution-chain view. It selects the **final execution block hash**, not the original code block hash or a beacon root. Copying the observed checkpoint from the ancestry file tests equality only; the tool cannot authenticate its origin. An ancestry or review document cannot grant itself trust through an embedded flag. A wrong separate hash fails with no partial result.

The review schema is exactly `code-frontier-review-v1` with integer `chain_id: 1`, `source_target`, integer uint64 `max_age_blocks`, and 1–96 unique `{address, code_hash}` rows, including the source. No wildcard is accepted. Addresses and deployed-runtime Ethereum Keccak hashes must match the entire visible runtime set. Compiler metadata is included in the hash. The normalized review digest remains in the output. Runtime-set changes, empty targets, proxy routing candidates and open call sites still refuse even when parent links and the supplied checkpoint hash match.

**Age stays tied to the original code block.** The reference height must be at least the checkpoint height. The maximum age is inclusive: an eight-block-old proof passes an eight-block age requirement and fails a seven-block one. A later checkpoint never refreshes code evidence or proves code at that checkpoint. The output records both blocks, original age, links per bundle, proof count/roots, provenance, and all inherited unknown sites.

| Exit | Meaning |
| --- | --- |
| 0 | Exact reviewed identities and age requirement match the bounded scan; every parent link and separately supplied checkpoint hash match. |
| 3 | Valid evidence with one or more requirements refusing it; structured JSON reasons. |
| 1 | Invalid input, corrupted raw evidence, broken ancestry, wrong anchor or conflicting context; no JSON on stdout. |
| 2 | Argument syntax error. |

The demo exits 0 when its expected refusals occur. No exit authorizes a transaction. An accepted bounded scan does not prove complete dependencies, EVM reachability, proxy routing semantics, source equivalence, unchanged code between blocks, later/current code, consensus/finality, checkpoint authenticity or semantic safety. A worker must independently trust the review, anchor and reference height.

Inputs must resolve inside the current workspace and be at most 100,000 bytes each. Duplicate JSON keys and non-finite numbers are refused. The program prints JSON and writes nothing; it never reads environment variables or accesses keys, wallets, secrets, signatures, transactions, payments, posts or deployments.

All runtime dependencies are committed ordinary sibling Python files: `code-frontier-review`, `code-dependency-frontier`, `code-targets`, `code-calls`, `code-surface`, `code-opcodes`, `code-ancestry`, `code-proof`, and `code-lens` (including Keccak). The demonstration also reads the already committed proof and ancestry documents plus its example review lists. No package, configuration change, submodule or new coin is needed.

Focused checks:

```sh
python3 -B -m unittest discover -s line-3/tools/code-frontier-checkpoint -p 'test_*.py' -v
```

All **18 tests passed**: real historical evidence; missing and copied comparison-only anchors; age boundaries; code-block/checkpoint substitution; rehashed wrong parents; reordered/missing/repeated headers; embedded trust flags; corrupt/forged runtime proofs; preserved IMD unknowns; every supplied target proof checked; wrong-block/unrelated/duplicate/excess proofs; exact review mismatches; input immutability; JSON size/key/number/path boundaries; and CLI exits with empty stdout on errors. The multi-target test uses real saved IMD/target proofs with explicitly synthetic descendant headers in memory to exercise linkage for both bundles. Synthetic headers and altered code are test fixtures only, never saved or presented as real-chain evidence.

The wall mark means: **Pepe links old code stones to a later checkpoint while keeping unfinished trails visible.**
