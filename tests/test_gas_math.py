"""Unit tests for honest gas math and step reduction calculations (Criterion 03)."""

import pytest
from batch.gas_math import (
    calculate_theoretical_gas_comparison,
    compute_receipt_verified_gas_comparison,
    GasComparisonReport
)
from batch.config import BASE_TX_INTRINSIC_GAS


def test_theoretical_gas_comparison_three_actions():
    """Verify deterministic intrinsic gas calculations for 3 actions."""
    report = calculate_theoretical_gas_comparison(action_count=3)

    # 1. Step metrics
    assert report.standalone_transaction_count == 3
    assert report.batched_transaction_count == 1
    assert report.confirmation_steps_eliminated == 2

    # 2. Intrinsic base gas metrics (21,000 per tx)
    assert report.base_tx_intrinsic_gas == BASE_TX_INTRINSIC_GAS  # 21,000
    assert report.standalone_total_intrinsic_gas == 3 * 21000     # 63,000
    assert report.batched_total_intrinsic_gas == 1 * 21000        # 21,000
    assert report.theoretical_intrinsic_gas_overhead_avoided == 42000

    # 3. Must be explicitly flagged as theoretical estimate only
    assert report.is_theoretical_estimate_only is True
    assert "Intrinsic gas savings are based strictly on 21,000 base overhead" in report.notice

    # 4. Measured & receipt fields must be None initially
    assert report.standalone_measured_execution_gas is None
    assert report.receipt_batched_gas_used is None


def test_theoretical_gas_comparison_invalid_count():
    """Reject action count < 1."""
    with pytest.raises(ValueError, match="Action count must be >= 1"):
        calculate_theoretical_gas_comparison(0)


def test_receipt_verified_gas_comparison():
    """Verify gas comparison when populated with genuine on-chain transaction receipts."""
    # Suppose 3 standalone transactions consumed: 21,000, 45,000, 32,000 = 98,000 total
    standalone_receipts = [21000, 45000, 32000]
    # Suppose batched transaction consumed: 68,000
    batched_receipt = 68000

    report = compute_receipt_verified_gas_comparison(
        action_count=3,
        standalone_receipt_gas_list=standalone_receipts,
        batched_receipt_gas=batched_receipt
    )

    assert report.receipt_standalone_gas_used_sum == 98000
    assert report.receipt_batched_gas_used == 68000
    assert report.receipt_actual_gas_saved == 30000
    assert report.receipt_actual_savings_percentage == 30.61
    assert report.is_theoretical_estimate_only is False
    assert "Verified from real on-chain receipts" in report.notice


def test_receipt_verified_mismatched_counts():
    """Raise error if number of standalone receipts does not match action_count."""
    with pytest.raises(ValueError, match="Expected 3 standalone receipts, but got 2"):
        compute_receipt_verified_gas_comparison(
            action_count=3,
            standalone_receipt_gas_list=[21000, 45000],
            batched_receipt_gas=50000
        )


def test_to_dict_structure():
    """Verify dictionary serialization preserves all categorized fields."""
    report = calculate_theoretical_gas_comparison(action_count=4)
    d = report.to_dict()

    assert "step_metrics" in d
    assert d["step_metrics"]["confirmation_steps_eliminated"] == 3
    assert "intrinsic_gas_metrics" in d
    assert d["intrinsic_gas_metrics"]["theoretical_intrinsic_gas_overhead_avoided"] == 63000
    assert "measured_execution_metrics" in d
    assert "receipt_metrics" in d
    assert d["status"]["is_theoretical_estimate_only"] is True
