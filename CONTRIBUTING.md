# Contributing to Pharos Batch Executor

Thank you for your interest in contributing to `pharos-batch-executor`!

## Code of Conduct & Core Invariants

1. **Zero Mocks Policy**:
   - Tests and runtime routines must never use mock RPC responses, simulated blockchain states, or synthetic receipts to fake on-chain behavior.
   - All network interactions must interface directly with live Pharos Atlantic Testnet RPC endpoints (`https://atlantic.dplabs-internal.com`).
   - Pure unit tests verifying ABI encoding and math must use explicitly defined mathematical test vectors.

2. **MultiCall3 Batching Constraints**:
   - Any valid batch manifest MUST contain at least three independent actions (`len(actions) >= 3`).
   - Every batch must handle partial failure (`requireSuccess=false`) using `tryAggregate` unless atomic failure is explicitly requested.
   - Revert bytes must be parsed through `decode_revert_data` to extract standard `Error(string)` and `Panic(uint256)` strings.

3. **Honest Gas Accounting**:
   - Always clearly distinguish between theoretical base intrinsic gas savings ($(N - 1) \times 21,000$) and net execution gas.
   - Never claim guaranteed blanket gas reduction percentages without transaction receipt evidence.

4. **Safety & Zero-Broadcast Invariant**:
   - No private keys, mnemonic phrases, or signer credentials may be committed or stored in this repository.
   - Automated scripts must rely on read-only EVM calls (`eth_call`).

## Development Workflow

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run test suite:
   ```bash
   pytest -v
   ```
3. Test CLI operations:
   ```bash
   python cli.py status
   python cli.py run manifests/atlantic_partial_failure.json
   ```
4. Verify code formatting and linting:
   ```bash
   python -m compileall .
   ```
