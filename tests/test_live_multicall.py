"""Live integration tests against Pharos Atlantic Testnet (Chain ID 688689).

These tests require an active internet connection to https://atlantic.dplabs-internal.com.
They perform purely non-mutating eth_call read operations against MultiCall3.
"""

import pytest
from batch.client import PharosBatchClient
from batch.config import MULTICALL3_ADDRESS, USDC_ADDRESS, CHAIN_ID
from batch.manifest import BatchManifest, ActionItem
from batch.encoding import encode_get_eth_balance_call
from eth_abi import encode
from web3 import Web3


@pytest.fixture(scope="module")
def live_client():
    client = PharosBatchClient()
    # Verify connectivity
    try:
        cid = client.get_chain_id()
        assert cid == CHAIN_ID
    except Exception as e:
        pytest.skip(f"Live Atlantic RPC unreachable: {e}")
    return client


def test_live_chain_id_and_block_number(live_client: PharosBatchClient):
    """Verify live node reports Chain ID 688689 and an advancing block height."""
    cid = live_client.get_chain_id()
    assert cid == 688689

    block = live_client.get_block_number()
    assert isinstance(block, int)
    assert block > 32_000_000


def test_live_multicall3_bytecode_presence(live_client: PharosBatchClient):
    """Verify MultiCall3 bytecode is present on Atlantic Testnet."""
    code = live_client.get_code(MULTICALL3_ADDRESS)
    assert code.startswith("0x")
    # Deployed contract bytecode is 7618 bytes
    assert len(code) > 1000


def test_live_three_action_all_success_batch(live_client: PharosBatchClient):
    """Verify a live 3-action read batch where all calls succeed."""
    wallet = "0xcc8475078f3C13975AcaA72F2B824097551Ca768"
    manifest = BatchManifest(
        title="Live 3-Action Success Batch",
        require_success=False,
        actions=[
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data="0x42cbb15c",  # getBlockNumber()
                expected_result_type="uint256"
            ),
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data="0x0f28c97d",  # getCurrentBlockTimestamp()
                expected_result_type="uint256"
            ),
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data=encode_get_eth_balance_call(wallet),
                expected_result_type="uint256"
            )
        ]
    )

    result = live_client.execute_read_batch(manifest)

    assert result.report.total_actions == 3
    assert result.report.successful_actions == 3
    assert result.report.failed_actions == 0
    assert result.report.all_succeeded is True

    # Block number should be > 32,000,000
    assert result.report.results[0].decoded_value > 32_000_000
    # Timestamp should be valid unix epoch (around 1.79 billion)
    assert result.report.results[1].decoded_value > 1_700_000_000
    # Balance should be int >= 0
    assert result.report.results[2].decoded_value >= 0


def test_live_partial_failure_revert_string(live_client: PharosBatchClient):
    """
    Verify live partial failure handling where Call 2 reverts on-chain with
    'ERC20: transfer amount exceeds allowance' while Calls 1 and 3 succeed.
    """
    # transferFrom(0x1, 0x2, 1000000) on USDC without allowance reverts
    tf_selector = Web3.keccak(text="transferFrom(address,address,uint256)")[:4].hex()
    sender = Web3.to_checksum_address("0x0000000000000000000000000000000000000001")
    recipient = Web3.to_checksum_address("0x0000000000000000000000000000000000000002")
    reverting_calldata = "0x" + tf_selector + encode(["address", "address", "uint256"], [sender, recipient, 1000000]).hex()

    manifest = BatchManifest(
        title="Live 3-Action Partial Failure Batch",
        require_success=False,
        actions=[
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data="0x42cbb15c",  # getBlockNumber()
                expected_result_type="uint256"
            ),
            ActionItem(
                target=USDC_ADDRESS,
                call_data=reverting_calldata,  # Reverting call
                expected_result_type=None
            ),
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data="0x0f28c97d",  # getCurrentBlockTimestamp()
                expected_result_type="uint256"
            )
        ]
    )

    result = live_client.execute_read_batch(manifest)

    assert result.report.total_actions == 3
    assert result.report.successful_actions == 2
    assert result.report.failed_actions == 1
    assert result.report.all_succeeded is False

    # Action 1: Succeeded
    assert result.report.results[0].success is True
    assert result.report.results[0].decoded_value > 32_000_000

    # Action 2: Reverted with Error(string)
    a2 = result.report.results[1]
    assert a2.success is False
    assert a2.is_revert is True
    assert a2.revert_type == "Error"
    assert a2.revert_message == "ERC20: transfer amount exceeds allowance"

    # Action 3: Succeeded (proves tryAggregate preserves surviving calls)
    assert result.report.results[2].success is True
    assert result.report.results[2].decoded_value > 1_700_000_000
