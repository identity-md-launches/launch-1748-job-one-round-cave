# Approval Event Backfill

Closes one missing interval in a saved ZTO or IMD `Approval`-event scan using public Ethereum logs and block headers. It works when an archive RPC can serve logs but cannot serve historical token state. It joins the backfill to two validated Allowance Lens windows, reports newly discovered owner–spender pairs, and explicitly requires a later same-block allowance recheck. It uses Python 3.10+ and only the standard library, plus the adjacent shipped Approval Coverage Map and Allowance Lens sources.

## One command

From the repository root, replay the bundled **real ZTO** backfill without network access:

```sh
python3 -B line-2/tools/approval-backfill/approval_backfill.py
```

On 2026-10-14, PublicNode supplied six real Approval logs in the previously unscanned 555-block interval **26,183,752–26,184,306**. Five owner–spender pairs had not appeared in the 19-pair earlier scan. The joined known set is now **24 pairs** across the continuous event window 26,182,252–26,184,356. The exact raw log/header evidence is `gap-events.json`. The saved later window is empty; it does not clear older permissions.

PublicNode refused the full Allowance Lens capture at the gap's end block with `historical state ... is not available`. dRPC returned HTTP 400. This tool therefore does **not** guess historical allowances. All 24 known pairs remain listed under `known_pairs_requiring_same_block_recheck`. The backfill closes only the finite event gap, not a wallet audit or a permission-policy decision.

To capture a different exact gap with read-only public RPC calls, supply two validated unfiltered Approval-window observations and a new output path:

```sh
python3 -B line-2/tools/approval-backfill/approval_backfill.py --before line-2/tools/allowance-lens/observation.json --after line-2/tools/allowance-changes/lens-recheck.json --fill line-2/tools/approval-backfill/new-gap-events.json --capture
```

The example path must not already exist. The tool validates the old windows before network access, limits the gap to 2,000 blocks and 128 logs, checks Ethereum chain 1, reads log chunks of at most 250 blocks, checks each log against a canonical block header, rereads the end header, validates the whole result, then saves only complete evidence. The overall capture has a process-enforced deadline of 90 seconds by default. The endpoint must be `https://ethereum-rpc.publicnode.com` or `https://eth.drpc.org`. The HTTP User-Agent is `IdentityMD-Pepeolithic-Line2-ApprovalBackfill/1.0`. No environment proxy lookup, wallet, key, signing, simulation, transaction submission, payment or posting is used.

Replay rejects a shortened fill, token or owner-filter mismatch, malformed logs, inconsistent log headers, and more than 64 distinct known pairs. Input JSON is bounded to 96 KiB and rejects duplicate keys through the adjacent loader. This is trusted public RPC evidence, not cryptographic proof of consensus or present canonicality. Approvals before the chosen interval can persist; Permit2 sub-permissions, unused signatures, unknown spenders, and nonstandard permissions remain outside coverage. A current allowance audit must reread all known pairs at one block before applying a policy.
