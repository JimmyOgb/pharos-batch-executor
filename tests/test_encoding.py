"""Unit tests for ABI encoding of MultiCall3 calldata (Criterion 02)."""

import pytest
from eth_abi import decode
from batch.config import (
    MULTICALL3_ADDRESS,
    SELECTOR_TRY_AGGREGATE,
    SELECTOR_AGGREGATE3,
    SELECTOR_GET_BLOCK_NUMBER,
    SELECTOR_GET_BLOCK_TIMESTAMP
)
from batch.manifest import ActionItem, BatchManifest
from batch.encoding import (
    encode_try_aggregate,
    encode_aggregate3,
    encode_erc20_balance_of,
    encode_erc20_allowance,
    encode_erc20_transfer,
    encode_erc20_approve,
    encode_get_eth_balance_call
)


@pytest.fixture
def sample_manifest() -> BatchManifest:
    return BatchManifest(
        title="Encoding Test Manifest",
        require_success=False,
        actions=[
            ActionItem(target=MULTICALL3_ADDRESS, call_data="0x42cbb15c", allow_failure=True),
            ActionItem(target=MULTICALL3_ADDRESS, call_data="0x0f28c97d", allow_failure=True),
            ActionItem(target=MULTICALL3_ADDRESS, call_data="0x4d2301cc", allow_failure=False)
        ]
    )


def test_encode_try_aggregate(sample_manifest: BatchManifest):
    """Test encoding tryAggregate(bool requireSuccess, (address,bytes)[] calls)."""
    calldata = encode_try_aggregate(sample_manifest)

    # Must start with selector 0xbce38bd7
    assert calldata.startswith(SELECTOR_TRY_AGGREGATE)

    # Decode parameters to verify exact ABI compliance
    payload = bytes.fromhex(calldata[len(SELECTOR_TRY_AGGREGATE):])
    require_success, calls = decode(["bool", "(address,bytes)[]"], payload)

    assert require_success is False
    assert len(calls) == 3
    assert calls[0][0].lower() == MULTICALL3_ADDRESS.lower()
    assert calls[0][1] == bytes.fromhex("42cbb15c")
    assert calls[1][1] == bytes.fromhex("0f28c97d")
    assert calls[2][1] == bytes.fromhex("4d2301cc")


def test_encode_aggregate3(sample_manifest: BatchManifest):
    """Test encoding aggregate3((address,bool,bytes)[] calls)."""
    calldata = encode_aggregate3(sample_manifest)

    # Must start with selector 0x82ad56cb
    assert calldata.startswith(SELECTOR_AGGREGATE3)

    # Decode parameters to verify exact ABI compliance
    payload = bytes.fromhex(calldata[len(SELECTOR_AGGREGATE3):])
    (calls,) = decode(["(address,bool,bytes)[]"], payload)

    assert len(calls) == 3
    assert calls[0][0].lower() == MULTICALL3_ADDRESS.lower()
    assert calls[0][1] is True  # allow_failure
    assert calls[0][2] == bytes.fromhex("42cbb15c")

    assert calls[2][1] is False  # allow_failure set to False on 3rd action


def test_encode_erc20_balance_of():
    """Test encoding balanceOf(address) with selector 0x70a08231."""
    owner = "0xcc8475078f3C13975AcaA72F2B824097551Ca768"
    cd = encode_erc20_balance_of(owner)
    assert cd.startswith("0x70a08231")

    # Decode address parameter
    param_bytes = bytes.fromhex(cd[10:])
    (decoded_owner,) = decode(["address"], param_bytes)
    assert decoded_owner.lower() == owner.lower()


def test_encode_erc20_transfer():
    """Test encoding transfer(address,uint256) with selector 0xa9059cbb."""
    recipient = "0xcc8475078f3C13975AcaA72F2B824097551Ca768"
    amount = 1_000_000  # 1 USDC (6 decimals)
    cd = encode_erc20_transfer(recipient, amount)
    assert cd.startswith("0xa9059cbb")

    param_bytes = bytes.fromhex(cd[10:])
    rec, amt = decode(["address", "uint256"], param_bytes)
    assert rec.lower() == recipient.lower()
    assert amt == amount


def test_encode_get_eth_balance_call():
    """Test encoding getEthBalance(address) with selector 0x4d2301cc."""
    account = "0xcc8475078f3C13975AcaA72F2B824097551Ca768"
    cd = encode_get_eth_balance_call(account)
    assert cd.startswith("0x4d2301cc")

    param_bytes = bytes.fromhex(cd[10:])
    (dec_acc,) = decode(["address"], param_bytes)
    assert dec_acc.lower() == account.lower()
