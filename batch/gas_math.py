"""Honest gas metrics and step reduction analysis for EVM batch execution."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from batch.config import BASE_TX_INTRINSIC_GAS


@dataclass
class GasComparisonReport:
    """
    Rigorously distinguishes theoretical intrinsic gas calculations
    from measured on-chain execution gas and receipt data.
    """
    # 1. Step & Confirmation Metrics
    standalone_transaction_count: int
    batched_transaction_count: int
    confirmation_steps_eliminated: int

    # 2. Intrinsic Base Gas (EVM Standard: 21,000 gas per tx header)
    base_tx_intrinsic_gas: int
    standalone_total_intrinsic_gas: int
    batched_total_intrinsic_gas: int
    theoretical_intrinsic_gas_overhead_avoided: int

    # 3. Execution Gas & Measured Gas
    standalone_measured_execution_gas: Optional[int] = None
    batched_measured_execution_gas: Optional[int] = None
    net_measured_gas_difference: Optional[int] = None

    # 4. Receipt Data (from actual on-chain receipts)
    receipt_standalone_gas_used_sum: Optional[int] = None
    receipt_batched_gas_used: Optional[int] = None
    receipt_actual_gas_saved: Optional[int] = None
    receipt_actual_savings_percentage: Optional[float] = None

    # Explicit indicator that arithmetic-only metrics are theoretical
    is_theoretical_estimate_only: bool = True
    notice: str = (
        "NOTE: Intrinsic gas savings are based strictly on 21,000 base overhead per transaction. "
        "Actual net gas delta depends on MultiCall contract execution overhead and must be "
        "verified from live on-chain transaction receipts."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization and API / UI consumption."""
        return {
            "step_metrics": {
                "standalone_transaction_count": self.standalone_transaction_count,
                "batched_transaction_count": self.batched_transaction_count,
                "confirmation_steps_eliminated": self.confirmation_steps_eliminated,
            },
            "intrinsic_gas_metrics": {
                "base_tx_intrinsic_gas": self.base_tx_intrinsic_gas,
                "standalone_total_intrinsic_gas": self.standalone_total_intrinsic_gas,
                "batched_total_intrinsic_gas": self.batched_total_intrinsic_gas,
                "theoretical_intrinsic_gas_overhead_avoided": self.theoretical_intrinsic_gas_overhead_avoided,
            },
            "measured_execution_metrics": {
                "standalone_measured_execution_gas": self.standalone_measured_execution_gas,
                "batched_measured_execution_gas": self.batched_measured_execution_gas,
                "net_measured_gas_difference": self.net_measured_gas_difference,
            },
            "receipt_metrics": {
                "receipt_standalone_gas_used_sum": self.receipt_standalone_gas_used_sum,
                "receipt_batched_gas_used": self.receipt_batched_gas_used,
                "receipt_actual_gas_saved": self.receipt_actual_gas_saved,
                "receipt_actual_savings_percentage": self.receipt_actual_savings_percentage,
            },
            "status": {
                "is_theoretical_estimate_only": self.is_theoretical_estimate_only,
                "notice": self.notice
            }
        }


def calculate_theoretical_gas_comparison(action_count: int) -> GasComparisonReport:
    """
    Calculate deterministic, theoretical intrinsic gas overhead and step reductions.
    Does NOT fabricate execution gas or receipt numbers.
    """
    if action_count < 1:
        raise ValueError(f"Action count must be >= 1, got {action_count}")

    standalone_tx_count = action_count
    batched_tx_count = 1
    steps_eliminated = standalone_tx_count - batched_tx_count

    standalone_intrinsic = standalone_tx_count * BASE_TX_INTRINSIC_GAS
    batched_intrinsic = batched_tx_count * BASE_TX_INTRINSIC_GAS
    overhead_avoided = standalone_intrinsic - batched_intrinsic

    return GasComparisonReport(
        standalone_transaction_count=standalone_tx_count,
        batched_transaction_count=batched_tx_count,
        confirmation_steps_eliminated=steps_eliminated,
        base_tx_intrinsic_gas=BASE_TX_INTRINSIC_GAS,
        standalone_total_intrinsic_gas=standalone_intrinsic,
        batched_total_intrinsic_gas=batched_intrinsic,
        theoretical_intrinsic_gas_overhead_avoided=overhead_avoided,
        is_theoretical_estimate_only=True
    )


def compute_receipt_verified_gas_comparison(
    action_count: int,
    standalone_receipt_gas_list: list[int],
    batched_receipt_gas: int
) -> GasComparisonReport:
    """
    Compute actual, measured gas savings from real on-chain transaction receipts.
    Requires genuine receipt gasUsed numbers.
    """
    if len(standalone_receipt_gas_list) != action_count:
        raise ValueError(
            f"Expected {action_count} standalone receipts, but got {len(standalone_receipt_gas_list)}"
        )

    standalone_total = sum(standalone_receipt_gas_list)
    actual_saved = standalone_total - batched_receipt_gas
    pct = (actual_saved / standalone_total * 100.0) if standalone_total > 0 else 0.0

    report = calculate_theoretical_gas_comparison(action_count)
    report.receipt_standalone_gas_used_sum = standalone_total
    report.receipt_batched_gas_used = batched_receipt_gas
    report.receipt_actual_gas_saved = actual_saved
    report.receipt_actual_savings_percentage = round(pct, 2)
    report.is_theoretical_estimate_only = False
    report.notice = (
        f"Verified from real on-chain receipts: standalone sum = {standalone_total:,} gas units, "
        f"batched = {batched_receipt_gas:,} gas units, net saved = {actual_saved:,} gas units ({pct:.1f}%)."
    )

    return report
