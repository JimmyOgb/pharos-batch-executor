"""Unit tests for batch manifest validation (Criterion 01: minimum 3 actions)."""

import pytest
from batch.manifest import ActionItem, BatchManifest, ManifestValidationError
from batch.config import MULTICALL3_ADDRESS, USDC_ADDRESS, WPHRS_ADDRESS


def test_action_item_valid():
    """Valid ActionItem with checksummed or lowercase address passes."""
    action = ActionItem(
        target=MULTICALL3_ADDRESS,
        call_data="0x42cbb15c",
        description="Check block number"
    )
    assert action.target == MULTICALL3_ADDRESS.lower()
    assert action.call_data == "0x42cbb15c"
    assert action.value == 0


def test_action_item_invalid_target():
    """Invalid address format raises ManifestValidationError."""
    with pytest.raises(ManifestValidationError, match="Invalid target EVM address"):
        ActionItem(target="0xInvalidAddressLength", call_data="0x")


def test_action_item_invalid_calldata_odd_length():
    """Odd-length calldata raises ManifestValidationError."""
    with pytest.raises(ManifestValidationError, match="length must be even"):
        ActionItem(target=MULTICALL3_ADDRESS, call_data="0x123")


def test_action_item_invalid_calldata_non_hex():
    """Non-hex characters in calldata raise ManifestValidationError."""
    with pytest.raises(ManifestValidationError, match="Invalid call data hex string"):
        ActionItem(target=MULTICALL3_ADDRESS, call_data="0xZZZZ")


def test_manifest_rejects_fewer_than_three_actions():
    """Criterion 01: Manifest with 0, 1, or 2 actions MUST be rejected."""
    action1 = ActionItem(target=MULTICALL3_ADDRESS, call_data="0x42cbb15c")
    action2 = ActionItem(target=USDC_ADDRESS, call_data="0x")

    # 0 actions
    with pytest.raises(ManifestValidationError, match="mandates a list of at least 3 independent actions"):
        BatchManifest(actions=[])

    # 1 action
    with pytest.raises(ManifestValidationError, match="mandates a list of at least 3 independent actions"):
        BatchManifest(actions=[action1])

    # 2 actions
    with pytest.raises(ManifestValidationError, match="mandates a list of at least 3 independent actions"):
        BatchManifest(actions=[action1, action2])


def test_manifest_accepts_three_or_more_actions():
    """Criterion 01: Manifest with >= 3 actions succeeds."""
    action1 = ActionItem(target=MULTICALL3_ADDRESS, call_data="0x42cbb15c", description="Block")
    action2 = ActionItem(target=MULTICALL3_ADDRESS, call_data="0x0f28c97d", description="Timestamp")
    action3 = ActionItem(target=USDC_ADDRESS, call_data="0x", description="USDC check")

    manifest = BatchManifest(actions=[action1, action2, action3])
    assert len(manifest.actions) == 3

    # Add a 4th action
    action4 = ActionItem(target=WPHRS_ADDRESS, call_data="0x", description="WPHRS check")
    manifest.add_action(action4)
    assert len(manifest.actions) == 4


def test_manifest_from_dict():
    """Can construct and validate manifest from structured JSON / dictionary."""
    data = {
        "title": "Three Action Test Batch",
        "require_success": False,
        "actions": [
            {"target": MULTICALL3_ADDRESS, "call_data": "0x42cbb15c", "description": "Call 1"},
            {"target": MULTICALL3_ADDRESS, "call_data": "0x0f28c97d", "description": "Call 2"},
            {"target": USDC_ADDRESS, "call_data": "0x", "description": "Call 3"}
        ]
    }
    manifest = BatchManifest.from_dict(data)
    assert manifest.title == "Three Action Test Batch"
    assert len(manifest.actions) == 3
    assert manifest.require_success is False
