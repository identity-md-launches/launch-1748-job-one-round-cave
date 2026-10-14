# ZTO Witness Packet

Give another worker one portable JSON file containing the **raw ZTO/IMD pool and Quoter captures** needed to recompute a swap planning bound offline. The receiver supplies their own source/group policy and quorum separately. A packet cannot install a sender's policy, substitute a precomputed report, or point the reviewer at external evidence files. Only Python's standard library and the committed sibling Line 1 Quorum, Policy, Replay, Witness, Path and Band sources are used; retain those folders when copying the tool.

From the repository root, one command shows it working without network access:

```sh
python3 -B line-1/tools/zto-witness-packet/zto_witness_packet.py --demo
```

The demo packages and replays the real historical 1-ZTO capture at Ethereum block **26,184,260**. Both entries are explicitly the same source. It prints `withheld`, `bound: null`, equal evidence fingerprints and duplicate-source/quorum reasons. Exit zero means the demonstration ran, not that a trade was approved. No second provider is claimed.

To package an existing receiver-authored `zto-witness-quorum-request-v1` request, run:

```sh
python3 -B line-1/tools/zto-witness-packet/zto_witness_packet.py --pack line-1/tools/zto-witness-packet/demo-request.json
```

This prints a compact packet to stdout; save stdout to a new workspace JSON file for a handoff. It reads each candidate snapshot and Quoter file once, checks the captured objects in memory, and carries only raw captures, input direction, amount and slippage. Malformed evidence is refused. Evidence with an honest withheld result may still be packaged. `demo-request.json` names committed real evidence and demonstrates why duplicating one capture does not establish a quorum.

For receiver review, the supplied fresh capture is also runnable offline:

```sh
python3 -B line-1/tools/zto-witness-packet/zto_witness_packet.py --packet line-1/tools/zto-witness-packet/live-packet.json --policy line-1/tools/zto-witness-packet/live-policy.json --minimum-distinct-groups 2 --expected-packet-sha256 8bb4c8dcb864ffa5d32bed119e7dbfe52d30b6e6139f185ea0bfa2eaee5c1cfb
```

This intentionally exits **2**, withholds a bound, and verifies the exact canonical packet fingerprint. The two packet entries are the same fresh capture. Replace the packet and policy paths with your own workspace files for actual review. `live-policy.json` is a captured demonstration policy anchored to its historical block, not a current receiver decision. Choose your own trusted block hash, reference height, maximum age, approved source labels and provider groups, token direction, input ceiling and slippage ceiling. Quorum is a separate receiver-selected integer from 2 to 8. Different directions are refused rather than silently reinterpreted.

The optional expected fingerprint is lowercase SHA-256 over JSON encoded with sorted keys, ASCII escaping and compact separators; whitespace and key order do not affect it. Obtain that fingerprint through your own trusted handoff if using it as an integrity check. Every review also records packet, policy and individual raw-capture fingerprints. Those identify content; they are not signatures or authentication of providers. JSON files and compact packets are capped at 100 KB; duplicate keys, floats and nonfinite numbers are refused. There are 2–8 inline capture pairs. Large capture sets must fit this size cap rather than be silently truncated.

What happened when tried: **15 focused tests passed**, including raw-return and amount tampering, changed fingerprints, sender-policy injection, receiver ceilings/age, ambiguous JSON, network refusal and an actual subprocess pack/review round trip. All **212 tests across 18 Line 1 suites** passed. The positive pair test is explicitly synthetic relabeling of historical data and tests plumbing only.

A fresh read through the assignment contributor's read-only transport captured finalized block **26,191,142** (`0x18fa526`), hash `0x6ae9df37c8e38f44e5ab0b31f3311acac2562022e1befc03dbcaf18c6e25d57c`. Both local traversal and the pinned deployed V4Quoter returned **18,807,962,790,798 raw IMD units**, or **0.000018807962790798 IMD**, for **1 ZTO**. The packet replays those bytes offline, then withholds because there is only one captured source. Public source reference: https://ethereum-rpc.publicnode.com. The assignment relay's actual upstream identity was not independently established. Capture metadata and the honest refusal are retained in `live-report.json`; no present-day freshness is claimed on later replay.

Exit codes: 0 for a completed demo, valid packing or accepted review; 2 for withheld review; 1 for malformed input, direction/fingerprint mismatch or file error. The tool reads workspace JSON and writes stdout. It makes no network requests and does not access environment variables, wallets, keys, secrets, signing, sends, payments, posts or deployments. Pool coverage, receiver provider assertions, unauthenticated RPC bytes, settlement, gas, MEV and future execution retain the ancestors' limitations. A packet is planning evidence, not an executable transaction.
