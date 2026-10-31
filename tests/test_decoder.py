"""Unit tests for decoding MultiCall3 return data and EVM revert payloads (Criterion 04)."""

import pytest
from eth_abi import encode
from batch.config import (
    SELECTOR_REVERT_ERROR,
    SELECTOR_REVERT_PANIC
)
from batch.decoder import (
    decode_revert_payload,
    decode_try_aggregate_return,
    ActionResult,
    BatchExecutionReport
)


def test_decode_revert_error_string():
    """Verify decoding of standard EVM Error(string) payload (selector 0x08c379a0)."""
    error_msg = "ERC20: transfer amount exceeds balance"
    sel_bytes = bytes.fromhex(SELECTOR_REVERT_ERROR[2:])
    param_bytes = encode(["string"], [error_msg])
    revert_data = sel_bytes + param_bytes

    rev_type, rev_msg, rev_code = decode_revert_payload(revert_data)
    assert rev_type == "Error"
    assert rev_msg == error_msg
    assert rev_code is None


def test_decode_revert_panic_arithmetic_overflow():
    """Verify decoding of standard EVM Panic(uint256) for arithmetic overflow (code 0x11)."""
    panic_code = 0x11
    sel_bytes = bytes.fromhex(SELECTOR_REVERT_PANIC[2:])
    param_bytes = encode(["uint256"], [panic_code])
    revert_data = sel_bytes + param_bytes

    rev_type, rev_msg, rev_code = decode_revert_payload(revert_data)
    assert rev_type == "Panic"
    assert rev_code == 0x11
    assert "Arithmetic operation underflowed or overflowed" in rev_msg


def test_decode_revert_panic_division_by_zero():
    """Verify decoding of standard EVM Panic(uint256) for division by zero (code 0x12)."""
    panic_code = 0x12
    sel_bytes = bytes.fromhex(SELECTOR_REVERT_PANIC[2:])
    param_bytes = encode(["uint256"], [panic_code])
    revert_data = sel_bytes + param_bytes

    rev_type, rev_msg, rev_code = decode_revert_payload(revert_data)
    assert rev_type == "Panic"
    assert rev_code == 0x12
    assert "Division or modulo by zero" in rev_msg


def test_decode_revert_empty():
    """Verify decoding of empty revert payload (0x)."""
    rev_type, rev_msg, rev_code = decode_revert_payload(b"")
    assert rev_type == "Empty"
    assert "without a reason string" in rev_msg
    assert rev_code is None


def test_decode_revert_custom_error():
    """Verify handling of custom error selector."""
    custom_bytes = bytes.fromhex("12345678deadbeef")
    rev_type, rev_msg, rev_code = decode_revert_payload(custom_bytes)
    assert rev_type == "Custom"
    assert "0x12345678" in rev_msg
    assert rev_code is None


def test_decode_partial_failure_three_actions():
    """
    Criterion 04: Verify partial failure decoding in a 3-action batch:
    Action 1: SUCCESS (uint256 block number 32,000,000)
    Action 2: REVERTED (Error(string): 'TransferHelper: TRANSFER_FAILED')
    Action 3: SUCCESS (uint256 timestamp 1,793,415,000)
    """
    val1_bytes = encode(["uint256"], [32000000])

    sel_err = bytes.fromhex(SELECTOR_REVERT_ERROR[2:])
    val2_bytes = sel_err + encode(["string"], ["TransferHelper: TRANSFER_FAILED"])

    val3_bytes = encode(["uint256"], [1793415000])

    # Construct ABI encoded (bool, bytes)[]
    raw_tuples = [
        (True, val1_bytes),
        (False, val2_bytes),
        (True, val3_bytes)
    ]
    encoded_return = encode(["(bool,bytes)[]"], [raw_tuples])
    raw_hex = "0x" + encoded_return.hex()

    report = decode_try_aggregate_return(
        raw_hex=raw_hex,
        expected_types=["uint256", None, "uint256"]
    )

    assert report.total_actions == 3
    assert report.successful_actions == 2
    assert report.failed_actions == 1
    assert report.all_succeeded is False

    # Action 1: Success
    res1 = report.results[0]
    assert res1.success is True
    assert res1.decoded_value == 32000000
    assert res1.is_revert is False

    # Action 2: Failure
    res2 = report.results[1]
    assert res2.success is False
    assert res2.is_revert is True
    assert res2.revert_type == "Error"
    assert res2.revert_message == "TransferHelper: TRANSFER_FAILED"

    # Action 3: Success (proves non-failing calls survive and decode)
    res3 = report.results[2]
    assert res3.success is True
    assert res3.decoded_value == 1793415000
    assert res3.is_revert is False

    # Summary table output check
    table = report.summary_table()
    assert "Total Actions: 3 | Succeeded: 2 | Failed: 1" in table
    assert "Action #1: SUCCESS" in table
    assert "Action #2: REVERTED [Error] | TransferHelper: TRANSFER_FAILED" in table
    assert "Action #3: SUCCESS" in table
