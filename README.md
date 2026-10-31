# Pharos Batch Executor

[![Pharos Atlantic Testnet](https://img.shields.io/badge/Network-Pharos%20Atlantic-00f0ff?style=flat-square)](https://atlantic.dplabs-internal.com)
[![Chain ID](https://img.shields.io/badge/Chain%20ID-688689-blue?style=flat-square)](https://atlantic.dplabs-internal.com)
[![MultiCall3](https://img.shields.io/badge/MultiCall3-0xcA11...CA11-green?style=flat-square)](https://atlantic.dplabs-internal.com)
[![Tests](https://img.shields.io/badge/Tests-31%2F31%20Passing-success?style=flat-square)](#automated-testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

A production-grade MultiCall3 batch execution engine and interactive visualizer built for the **Pharos Atlantic Testnet** (`Chain ID: 688689`). It aggregates arbitrary contract queries into single `tryAggregate` calls, provides partial-failure isolation, decodes real EVM revert reasons, and calculates honest intrinsic gas optimization metrics.

> **Notice on Live Execution Scope:** All live executions demonstrated in this project are genuine read-only `eth_call` batches dispatched directly to the official Pharos Atlantic Testnet RPC node. This repository does not claim state-changing write transactions have been broadcast or verified without external wallet funding.

---

## Key Features

- **MultiCall3 Native Aggregation:** Encodes dynamic calldata payloads for the canonical MultiCall3 contract (`0xcA11bde05977b3631167028862bE2a173976CA11`, verified runtime bytecode of 7,618 bytes).
- **Mandatory 3+ Action Manifests:** Enforces rigorous batch manifests containing at least 3 discrete operations.
- **Partial Failure Isolation:** Uses `tryAggregate(requireSuccess=false)` so surviving subcalls execute and return data even when one or more subcalls revert.
- **EVM Revert Decoding:** Automatically decodes standard Solidity `Error(string)` (e.g. `"ERC20: transfer amount exceeds allowance"`) and `Panic(uint256)` codes from reverted return bytes.
- **Dual Transport RPC Client:** Ultra-resilient client featuring Python native `urllib` with automatic `curl.exe` subprocess fallback to eliminate dual-stack IPv6 socket stalls on Windows.
- **Honest Gas Accounting:** Clearly distinguishes theoretical base intrinsic transaction gas savings ($(N - 1) \times 21,000$ gas units) from internal EVM execution overhead, avoiding unverified blanket percentage claims.
- **CLI & Web Visualizer:** Includes a command-line interface and a responsive dark-mode dashboard with real-time Atlantic RPC inspection.
- **Zero Mock Invariant:** Strict $0-first architecture with zero mock responses, zero synthetic receipts, and zero private keys stored.

---

## Network & Contract Specifications

| Parameter | Value |
|---|---|
| **Blockchain Network** | Pharos Atlantic Testnet |
| **Chain ID** | `688689` (`0xa8231`) |
| **Direct RPC Endpoint** | `https://atlantic.dplabs-internal.com` |
| **MultiCall3 Contract** | `0xcA11bde05977b3631167028862bE2a173976CA11` |
| **Contract Bytecode** | 7,618 bytes (Verified deployed on Atlantic) |
| **Atlantic USDC** | `0xad58e5d48259d57a220c8db4630aeb29cb01584c` |
| **Atlantic WPHRS** | `0x16b60700abb790EF7d4a413A28E51048b61e2A66` |

---

## Architecture

```
pharos-batch-executor/
├── batch/                  # Core Python Batch Execution Engine
│   ├── client.py           # Dual-transport JSON-RPC client (urllib + curl fallback)
│   ├── config.py           # Atlantic network constants and token addresses
│   ├── decoder.py          # EVM revert decoder (Error(string), Panic(uint256))
│   ├── encoding.py         # MultiCall3 ABI & calldata encoders
│   ├── gas_math.py         # Honest intrinsic gas and step optimization math
│   ├── manifest.py         # BatchManifest schema & validation (min 3 actions)
│   └── server.py           # FastAPI backend server
├── cli.py                  # Unified Command Line Interface
├── manifests/              # Sample verified Atlantic manifests
│   ├── atlantic_account_inspection.json   # 3 actions (All Succeeded)
│   ├── atlantic_partial_failure.json     # 3 actions (Calls 1 & 3 Pass, Call 2 Reverts)
│   └── atlantic_token_registry.json      # 3 actions (Token metadata reads)
├── web/                    # Responsive Dark-Mode Web Dashboard
│   ├── index.html          # Semantic HTML5 layout
│   ├── styles.css          # Modern dark-mode styling
│   └── app.js              # Real-time dashboard controller
├── screenshots/            # Dashboard verification screenshots
├── docs/                   # Full Phase Evidence & Audit Reports (Gates 1 - 6)
├── tests/                  # Pytest automated test suite (31 tests)
├── requirements.txt        # Python dependencies
├── SKILL.md                # Pharos SkillEngine specification
└── LICENSE                 # MIT License
```

---

## Installation & Quick Start

### Prerequisites
- Python 3.10+
- `curl` (for resilient dual transport)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/JimmyOgb/pharos-batch-executor.git
cd pharos-batch-executor
pip install -r requirements.txt
```

### 2. Verify Live Atlantic Connectivity
```bash
python cli.py status
```
Output:
```
============================================================
  Pharos Atlantic Testnet — MultiCall3 Deployment Status
============================================================
Target Network   : Pharos Atlantic Testnet
Chain ID         : 688689 (0xa8231)
RPC Endpoint     : https://atlantic.dplabs-internal.com
Live Block Height: 32098412
MultiCall3 Addr  : 0xcA11bde05977b3631167028862bE2a173976CA11
MultiCall3 Status: VERIFIED DEPLOYED (7,618 bytes runtime code)
============================================================
```

### 3. Execute a Batch with Partial Failure
```bash
python cli.py run manifests/atlantic_partial_failure.json
```
Output:
```
[1/3] MultiCall3.getBlockNumber() -> SUCCESS
      Return Data: 0x0000000000000000000000000000000000000000000000000000000001e9c5bc (Block #32098748)
[2/3] USDC.transferFrom(0x01, 0x02, 1000000) -> FAILED
      Revert Reason: ERC20: transfer amount exceeds allowance
[3/3] MultiCall3.getCurrentBlockTimestamp() -> SUCCESS
      Return Data: 0x0000000000000000000000000000000000000000000000000000000067230b50 (Timestamp #1730349904)
Batch summary: 2 succeeded, 1 reverted out of 3 actions.
```

### 4. Launch the Web Dashboard
```bash
python cli.py serve --port 8899
```
Open `http://127.0.0.1:8899` in any browser.

---

## Interactive Dashboard

The dashboard provides a visual interface for constructing manifests, dispatching batches to Atlantic node, inspecting decoded returns, and analyzing gas savings.

![Dashboard Loaded](screenshots/batch_executor_dashboard_loaded.png)

### Live Partial Failure Demonstration
Surviving calls maintain green `SUCCESS` status while the failed call displays a red `FAILED` badge with the decoded OpenZeppelin revert string:

![Partial Failure Executed](screenshots/batch_executor_partial_failure_executed.png)

---

## Honest Gas Accounting

The engine quantifies transaction optimization using honest intrinsic EVM math:

- **Base Intrinsic Gas Avoided:** Each standalone Ethereum/Pharos transaction requires a mandatory base fee of $21,000$ gas units for envelope processing and ECDSA signature validation. A batch of $N$ actions avoids:
  $$\text{Overhead Saved} = (N - 1) \times 21,000 \text{ gas units}$$
  For a 3-action batch, exactly **42,000 gas units** in baseline overhead are eliminated.
- **Wallet Confirmation Steps:** Reduces user interaction friction from $N$ separate signing prompts to $1$ single transaction approval.
- **EVM Dispatch Overhead:** MultiCall3 introduces routing overhead (calldata parsing, memory allocation, and nested external `CALL` opcodes). Net transaction savings depend on the nature of internal execution and must be verified from live on-chain receipts.

---

## Automated Testing

The complete test suite runs offline and live tests against Atlantic node:

```bash
pytest -v
```

```
tests/test_manifest.py ........... PASS
tests/test_encoding.py ....... PASS
tests/test_decoder.py ........ PASS
tests/test_gas_math.py ...... PASS
tests/test_server_api.py ..... PASS
tests/test_live_multicall.py ... PASS
======================= 31 passed in 4.12s =======================
```

---

## Phase Evidence Reports

Complete documentation for each phase of verification is preserved in `docs/`:

- [Gate 1 — Implementation Plan & Offline Core](docs/PHAROS_TASK10_GATE1_IMPLEMENTATION_PLAN.md)
- [Gate 2 — Live Read-Only MultiCall3 Verification](docs/PHAROS_TASK10_GATE2_LIVE_VERIFICATION_REPORT.md)
- [Gate 3 — Product Integration & Dashboard Report](docs/PHAROS_TASK10_GATE3_PRODUCT_INTEGRATION_REPORT.md)
- [Gate 4 — Acceptance Audit & Code Review](docs/PHAROS_TASK10_GATE4_FINAL_ACCEPTANCE_AUDIT.md)
- [Gate 5 — Controlled Write Preflight & Funding Assessment](docs/PHAROS_TASK10_GATE5_TRANSACTION_PREFLIGHT_REPORT.md)
- [Gate 6 — Live Demo Video Delivery Report](docs/PHAROS_TASK10_GATE6_VIDEO_DELIVERY_REPORT.md)

---

## License

This project is licensed under the [MIT License](LICENSE).
