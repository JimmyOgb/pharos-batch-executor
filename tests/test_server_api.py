"""API integration tests for FastAPI backend server."""

import pytest
from fastapi.testclient import TestClient
from batch.server import app
from batch.config import MULTICALL3_ADDRESS, USDC_ADDRESS

client = TestClient(app)


def test_api_status_endpoint():
    """Verify /api/status returns live Atlantic network parameters."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    assert "network" in data
    assert data["network"]["chain_id"] == 688689
    assert data["network"]["chain_id_hex"] == "0xa8231"
    assert data["network"]["block_number"] > 32_000_000

    assert "multicall3" in data
    assert data["multicall3"]["address"].lower() == MULTICALL3_ADDRESS.lower()
    assert data["multicall3"]["is_deployed"] is True
    assert data["multicall3"]["bytecode_length"] > 1000


def test_api_execute_rejects_fewer_than_three_actions():
    """Verify /api/execute returns 422 when fewer than 3 actions are submitted."""
    payload = {
        "title": "Invalid 2-Action Batch",
        "actions": [
            {"target": MULTICALL3_ADDRESS, "call_data": "0x42cbb15c"},
            {"target": MULTICALL3_ADDRESS, "call_data": "0x0f28c97d"}
        ]
    }
    response = client.post("/api/execute", json=payload)
    assert response.status_code == 422
    assert "at least 3 independent actions" in response.json()["detail"]


def test_api_execute_valid_live_three_actions():
    """Verify /api/execute dispatches a live MultiCall3 batch and returns honest gas analysis."""
    payload = {
        "title": "Live Test API Batch",
        "require_success": False,
        "actions": [
            {
                "target": MULTICALL3_ADDRESS,
                "call_data": "0x42cbb15c",
                "description": "Block Number",
                "expected_result_type": "uint256"
            },
            {
                "target": MULTICALL3_ADDRESS,
                "call_data": "0x0f28c97d",
                "description": "Timestamp",
                "expected_result_type": "uint256"
            },
            {
                "target": MULTICALL3_ADDRESS,
                "call_data": "0x42cbb15c",
                "description": "Repeat Block",
                "expected_result_type": "uint256"
            }
        ]
    }
    response = client.post("/api/execute", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Network metadata
    assert data["network"]["chain_id"] == 688689
    assert data["network"]["block_number"] > 32_000_000

    # Summary
    assert data["summary"]["total_actions"] == 3
    assert data["summary"]["successful_actions"] == 3
    assert data["summary"]["all_succeeded"] is True

    # Gas analysis included and flagged as theoretical
    assert "gas_analysis" in data
    gas = data["gas_analysis"]
    assert gas["step_metrics"]["confirmation_steps_eliminated"] == 2
    assert gas["intrinsic_gas_metrics"]["theoretical_intrinsic_gas_overhead_avoided"] == 42000
    assert gas["status"]["is_theoretical_estimate_only"] is True


def test_api_gas_analysis_endpoint():
    """Verify /api/gas-analysis returns honest theoretical metrics."""
    response = client.post("/api/gas-analysis", json={"action_count": 5})
    assert response.status_code == 200
    data = response.json()

    assert data["step_metrics"]["standalone_transaction_count"] == 5
    assert data["step_metrics"]["batched_transaction_count"] == 1
    assert data["step_metrics"]["confirmation_steps_eliminated"] == 4
    assert data["intrinsic_gas_metrics"]["theoretical_intrinsic_gas_overhead_avoided"] == 84000
    assert data["status"]["is_theoretical_estimate_only"] is True
