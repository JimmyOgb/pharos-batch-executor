"""ABI and calldata encoding for MultiCall3 on Pharos Atlantic Testnet."""

from typing import List, Tuple
from eth_abi import encode
from web3 import Web3
from batch.config import (
    SELECTOR_TRY_AGGREGATE,
    SELECTOR_AGGREGATE3,
    SELECTOR_AGGREGATE,
    SELECTOR_GET_BLOCK_NUMBER,
    SELECTOR_GET_BLOCK_TIMESTAMP,
    SELECTOR_GET_ETH_BALANCE,
    MULTICALL3_ADDRESS
)
from batch.manifest import ActionItem, BatchManifest


def encode_try_aggregate(manifest: BatchManifest) -> str:
    """
    Encode calldata for MultiCall3.tryAggregate(bool requireSuccess, (address,bytes)[] calls).
    Function selector: 0xbce38bd7
    """
    # calls: (address, bytes)[]
    calls_data = []
    for action in manifest.actions:
        target_address = Web3.to_checksum_address(action.target)
        call_bytes = bytes.fromhex(action.call_data[2:] if action.call_data.startswith("0x") else action.call_data)
        calls_data.append((target_address, call_bytes))

    encoded_params = encode(
        ["bool", "(address,bytes)[]"],
        [manifest.require_success, calls_data]
    )

    return SELECTOR_TRY_AGGREGATE + encoded_params.hex()


def encode_aggregate3(manifest: BatchManifest) -> str:
    """
    Encode calldata for MultiCall3.aggregate3((address,bool,bytes)[] calls).
    Function selector: 0x82ad56cb
    """
    # calls: (address, bool, bytes)[]
    calls_data = []
    for action in manifest.actions:
        target_address = Web3.to_checksum_address(action.target)
        call_bytes = bytes.fromhex(action.call_data[2:] if action.call_data.startswith("0x") else action.call_data)
        calls_data.append((target_address, action.allow_failure, call_bytes))

    encoded_params = encode(
        ["(address,bool,bytes)[]"],
        [calls_data]
    )

    return SELECTOR_AGGREGATE3 + encoded_params.hex()


# Helper function encoders for standard calls
def encode_erc20_balance_of(owner: str) -> str:
    """Encode standard ERC-20 balanceOf(address) calldata (selector 0x70a08231)."""
    selector = Web3.keccak(text="balanceOf(address)")[:4].hex()
    checksummed = Web3.to_checksum_address(owner)
    encoded = encode(["address"], [checksummed]).hex()
    return f"0x{selector}{encoded}"


def encode_erc20_allowance(owner: str, spender: str) -> str:
    """Encode standard ERC-20 allowance(address,address) calldata (selector 0xdd62ed3e)."""
    selector = Web3.keccak(text="allowance(address,address)")[:4].hex()
    c_owner = Web3.to_checksum_address(owner)
    c_spender = Web3.to_checksum_address(spender)
    encoded = encode(["address", "address"], [c_owner, c_spender]).hex()
    return f"0x{selector}{encoded}"


def encode_erc20_transfer(recipient: str, amount: int) -> str:
    """Encode standard ERC-20 transfer(address,uint256) calldata (selector 0xa9059cbb)."""
    selector = Web3.keccak(text="transfer(address,uint256)")[:4].hex()
    c_recipient = Web3.to_checksum_address(recipient)
    encoded = encode(["address", "uint256"], [c_recipient, amount]).hex()
    return f"0x{selector}{encoded}"


def encode_erc20_approve(spender: str, amount: int) -> str:
    """Encode standard ERC-20 approve(address,uint256) calldata (selector 0x095ea7b3)."""
    selector = Web3.keccak(text="approve(address,uint256)")[:4].hex()
    c_spender = Web3.to_checksum_address(spender)
    encoded = encode(["address", "uint256"], [c_spender, amount]).hex()
    return f"0x{selector}{encoded}"


def encode_get_eth_balance_call(account: str) -> str:
    """Encode MultiCall3.getEthBalance(address) calldata (selector 0x4d2301cc)."""
    selector = SELECTOR_GET_ETH_BALANCE[2:] if SELECTOR_GET_ETH_BALANCE.startswith("0x") else SELECTOR_GET_ETH_BALANCE
    c_account = Web3.to_checksum_address(account)
    encoded = encode(["address"], [c_account]).hex()
    return f"0x{selector}{encoded}"


def build_three_action_read_manifest(account: str, token_addr: str) -> BatchManifest:
    """Build a standard 3-action live inspection batch manifest."""
    return BatchManifest(
        title="Live Atlantic Account & Network MultiCall Inspection",
        require_success=False,
        actions=[
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data=f"{SELECTOR_GET_BLOCK_NUMBER}",
                description="Query current on-chain block number via MultiCall3",
                action_type="read",
                expected_result_type="uint256"
            ),
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data=f"{SELECTOR_GET_BLOCK_TIMESTAMP}",
                description="Query current block timestamp via MultiCall3",
                action_type="read",
                expected_result_type="uint256"
            ),
            ActionItem(
                target=MULTICALL3_ADDRESS,
                call_data=encode_get_eth_balance_call(account),
                description=f"Query native PHRS balance for {account}",
                action_type="read",
                expected_result_type="uint256"
            )
        ]
    )
