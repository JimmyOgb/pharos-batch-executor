"""Decoding return data and EVM revert payloads for MultiCall3 on Pharos."""

from dataclasses import dataclass
from typing import List, Optional, Any, Tuple
from eth_abi import decode
from web3 import Web3
from batch.config import (
    SELECTOR_REVERT_ERROR,
    SELECTOR_REVERT_PANIC,
    PANIC_CODES
)


@dataclass
class ActionResult:
    """Decoded result of a single action in the batch."""
    action_index: int
    success: bool
    raw_return_data: str
    decoded_value: Optional[Any] = None
    is_revert: bool = False
    revert_type: Optional[str] = None  # "Error", "Panic", "Custom", "Empty", None
    revert_message: Optional[str] = None
    revert_code: Optional[int] = None

    def summary(self) -> str:
        """Produce a readable diagnostic line."""
        if self.success:
            val_str = f"Decoded: {self.decoded_value}" if self.decoded_value is not None else f"Raw: {self.raw_return_data}"
            return f"Action #{self.action_index + 1}: SUCCESS | {val_str}"
        else:
            reason = self.revert_message or f"Revert code: {self.revert_code}" or self.raw_return_data
            return f"Action #{self.action_index + 1}: REVERTED [{self.revert_type}] | {reason}"


@dataclass
class BatchExecutionReport:
    """Complete summary of a batch execution outcome."""
    total_actions: int
    successful_actions: int
    failed_actions: int
    results: List[ActionResult]
    all_succeeded: bool

    def summary_table(self) -> str:
        """Generate a formatted markdown or CLI summary."""
        lines = [
            f"Total Actions: {self.total_actions} | Succeeded: {self.successful_actions} | Failed: {self.failed_actions}",
            "-" * 70
        ]
        for r in self.results:
            lines.append(r.summary())
        return "\n".join(lines)


def decode_revert_payload(data_bytes: bytes) -> Tuple[str, Optional[str], Optional[int]]:
    """
    Decode EVM revert data.
    Returns: (revert_type, revert_message, revert_code)
    """
    if not data_bytes or len(data_bytes) == 0:
        return ("Empty", "Reverted without a reason string or error data", None)

    hex_data = data_bytes.hex()
    selector = "0x" + hex_data[:8]

    # Standard Error(string): selector 0x08c379a0
    if selector.lower() == SELECTOR_REVERT_ERROR.lower() and len(data_bytes) >= 4:
        try:
            (msg,) = decode(["string"], data_bytes[4:])
            return ("Error", msg, None)
        except Exception as e:
            return ("Error", f"Failed to decode Error(string): {str(e)}", None)

    # Standard Panic(uint256): selector 0x4e487b71
    if selector.lower() == SELECTOR_REVERT_PANIC.lower() and len(data_bytes) >= 36:
        try:
            (code,) = decode(["uint256"], data_bytes[4:36])
            desc = PANIC_CODES.get(code, f"Unknown panic code {hex(code)}")
            return ("Panic", desc, code)
        except Exception as e:
            return ("Panic", f"Failed to decode Panic(uint256): {str(e)}", None)

    # Custom or unknown error
    return ("Custom", f"Custom error with selector {selector}", None)


def decode_try_aggregate_return(
    raw_hex: str,
    expected_types: Optional[List[Optional[str]]] = None
) -> BatchExecutionReport:
    """
    Decode the return bytes from MultiCall3.tryAggregate or aggregate3.
    ABI type: (bool, bytes)[]
    """
    if raw_hex.startswith("0x"):
        raw_hex = raw_hex[2:]

    if not raw_hex:
        return BatchExecutionReport(0, 0, 0, [], False)

    data_bytes = bytes.fromhex(raw_hex)
    (raw_results,) = decode(["(bool,bytes)[]"], data_bytes)

    action_results = []
    success_count = 0
    fail_count = 0

    for idx, (success, item_bytes) in enumerate(raw_results):
        item_hex = "0x" + item_bytes.hex()
        expected_type = expected_types[idx] if expected_types and idx < len(expected_types) else None

        if success:
            success_count += 1
            decoded_val = None
            if expected_type and item_bytes:
                try:
                    (decoded_val,) = decode([expected_type], item_bytes)
                except Exception:
                    decoded_val = item_hex
            else:
                decoded_val = item_hex

            action_results.append(ActionResult(
                action_index=idx,
                success=True,
                raw_return_data=item_hex,
                decoded_value=decoded_val,
                is_revert=False
            ))
        else:
            fail_count += 1
            rev_type, rev_msg, rev_code = decode_revert_payload(item_bytes)
            action_results.append(ActionResult(
                action_index=idx,
                success=False,
                raw_return_data=item_hex,
                decoded_value=None,
                is_revert=True,
                revert_type=rev_type,
                revert_message=rev_msg,
                revert_code=rev_code
            ))

    total = len(action_results)
    return BatchExecutionReport(
        total_actions=total,
        successful_actions=success_count,
        failed_actions=fail_count,
        results=action_results,
        all_succeeded=(fail_count == 0 and total > 0)
    )
