---
name: pharos-batch-executor
description: >
  MultiCall3 batch execution engine on Pharos Atlantic Testnet (Chain ID 688689).
  Encodes manifests with 3+ actions, executes tryAggregate read-only batches,
  isolates partial failures, decodes OpenZeppelin revert reasons, and calculates honest gas optimization metrics.
version: 0.1.0
requires:
  anyBins:
  - python3
  - python
---

# Pharos Batch Executor

A SkillEngine-compatible MultiCall3 aggregation engine for the Pharos Atlantic Testnet (`Chain ID: 688689`). It bundles arbitrary contract reads into single atomic or non-reverting `tryAggregate` batches, decodes individual call return values and EVM revert reasons, provides real-time CLI and Web UI interfaces, and enforces honest gas accounting.

## Capability Index

| Capability | Command / Endpoint | Description |
|---|---|---|
| **Query Live Network Status** | `python cli.py status` | Inspects Atlantic testnet block height, chain ID, and verifies MultiCall3 bytecode presence. |
| **Execute Batch Manifest** | `python cli.py run <manifest.json>` | Dispatches a MultiCall3 `tryAggregate` batch via live Atlantic RPC, isolating partial failures. |
| **Estimate Gas & Savings** | `python cli.py estimate <manifest.json>` | Calculates theoretical intrinsic gas saved ($(N - 1) \times 21,000$) and wallet steps avoided. |
| **Start Web Dashboard** | `python cli.py serve --port 8899` | Launches the interactive dark-mode visualizer with real-time on-chain results. |
| **Status API** | `GET /api/status` | REST endpoint returning chain status, block height, and MultiCall3 deployment info. |
| **Execute API** | `POST /api/execute` | REST endpoint accepting a BatchManifest JSON and returning decoded per-call outcomes. |
| **Gas Analysis API** | `POST /api/gas-analysis` | REST endpoint returning intrinsic gas math and honest execution disclaimers. |

## Agent Guidelines Block

When an autonomous AI agent or user needs to execute multiple EVM queries or bundled operations on Pharos Atlantic:

1. **Manifest Construction**:
   - Construct a `BatchManifest` containing at least **three** discrete actions (`len(actions) >= 3`).
   - Each action requires `target` (checksummed EVM address), `call_data` (hex string with 4-byte selector), and `description`.
   - Set `require_success=False` for non-reverting partial failure tolerance (`tryAggregate`), or `True` for atomic rollbacks.
2. **Execute MultiCall3 Batch**:
   - Call `PharosBatchClient.execute_batch(manifest)`.
   - The engine sends an `eth_call` to `0xcA11bde05977b3631167028862bE2a173976CA11`.
3. **Parse Per-Action Results & Reverts**:
   - Iterate over `BatchExecutionResult.results`.
   - If `res.success == True`: inspect `res.return_data`.
   - If `res.success == False`: inspect `res.revert_reason`. The engine decodes standard `Error(string)` (e.g. `"ERC20: transfer amount exceeds allowance"`) and `Panic(uint256)` codes.
4. **Honest Gas Disclosures**:
   - Never quote blanket gas percentage savings.
   - Base transaction gas avoided is strictly $(N - 1) \times 21,000$ gas units.
   - Net transaction savings depend on contract-internal loop overhead and require transaction receipt verification.

## Network & Contract Configuration

- **Target Network:** Pharos Atlantic Testnet
- **Chain ID:** `688689` (`0xa8231`)
- **Direct RPC Endpoint:** `https://atlantic.dplabs-internal.com`
- **MultiCall3 Address:** `0xcA11bde05977b3631167028862bE2a173976CA11`
- **Runtime Bytecode:** 7,618 bytes (Verified deployed on-chain)
- **Atlantic USDC:** `0xad58e5d48259d57a220c8db4630aeb29cb01584c`
- **Atlantic WPHRS:** `0x16b60700abb790EF7d4a413A28E51048b61e2A66`

## Manifest Schema

Manifests are JSON documents conforming to the following structure:

```json
{
  "title": "Account & Block Inspection",
  "require_success": false,
  "actions": [
    {
      "target": "0xcA11bde05977b3631167028862bE2a173976CA11",
      "call_data": "0x42cbb15c",
      "description": "MultiCall3.getBlockNumber()"
    },
    {
      "target": "0xad58e5d48259d57a220c8db4630aeb29cb01584c",
      "call_data": "0x23b872dd0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000f4240",
      "description": "USDC.transferFrom(0x01, 0x02, 1000000)"
    },
    {
      "target": "0xcA11bde05977b3631167028862bE2a173976CA11",
      "call_data": "0x0e5d8001",
      "description": "MultiCall3.getCurrentBlockTimestamp()"
    }
  ]
}
```

## Revert Data Decoding Specification

When a subcall reverts, MultiCall3 packs the raw return bytes into `returnData`. The engine decodes:
- **`0x08c379a0` (`Error(string)`):** Standard Solidity / OpenZeppelin revert messages (e.g. `"ERC20: transfer amount exceeds allowance"`).
- **`0x4e487b71` (`Panic(uint256)`):** EVM compiler-generated asserts (e.g. `0x01` assert false, `0x11` arithmetic overflow, `0x12` divide by zero, `0x32` array out of bounds).
- **Custom / Empty Errors:** Preserved as raw hex strings if unknown.

## Security Boundaries & Strict Invariants

- **Read-Only Default:** All live interactions use `eth_call`. No private keys or signers are required.
- **Fail-Safe Transport:** Dual-transport client uses Python standard library `urllib` with automatic `curl.exe` subprocess fallback to mitigate Windows IPv6 resolution latency.
- **Zero Mock Policy:** Synthetic RPC responses and simulated transactions are prohibited. If the node is unreachable, an explicit error state is emitted.
