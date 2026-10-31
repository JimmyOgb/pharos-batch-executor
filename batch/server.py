"""FastAPI backend server for Pharos Batch Executor web dashboard."""

import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from batch.config import (
    CHAIN_ID,
    CHAIN_ID_HEX,
    NETWORK_NAME,
    MULTICALL3_ADDRESS,
    DEFAULT_RPC_URL,
    USDC_ADDRESS,
    WPHRS_ADDRESS,
    MIN_BATCH_ACTIONS
)
from batch.client import PharosBatchClient, NetworkRPCError
from batch.manifest import BatchManifest, ManifestValidationError
from batch.gas_math import calculate_theoretical_gas_comparison

app = FastAPI(
    title="Pharos Batch Executor API",
    description="Real-data MultiCall3 batch execution engine on Pharos Atlantic Testnet",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = PharosBatchClient()

# Path to static frontend files
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")


@app.get("/api/status")
async def get_network_status() -> Dict[str, Any]:
    """Fetch live on-chain status from the Pharos Atlantic node."""
    try:
        cid = client.get_chain_id()
        block = client.get_block_number()
        code = client.get_code(MULTICALL3_ADDRESS)
        is_deployed = len(code) > 2
        code_length = len(code)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Pharos Atlantic node unreachable: {str(e)}"
        )

    return {
        "network": {
            "name": NETWORK_NAME,
            "chain_id": cid,
            "chain_id_hex": CHAIN_ID_HEX,
            "rpc_url": DEFAULT_RPC_URL,
            "block_number": block,
        },
        "multicall3": {
            "address": MULTICALL3_ADDRESS,
            "is_deployed": is_deployed,
            "bytecode_length": code_length,
        },
        "verified_tokens": {
            "USDC": USDC_ADDRESS,
            "WPHRS": WPHRS_ADDRESS,
        },
        "min_batch_actions": MIN_BATCH_ACTIONS
    }


@app.post("/api/execute")
async def execute_batch(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Execute a read-only batch against MultiCall3 on Atlantic Testnet."""
    try:
        manifest = BatchManifest.from_dict(payload)
    except ManifestValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid manifest payload: {str(e)}")

    try:
        result = client.execute_read_batch(manifest)
    except NetworkRPCError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

    response_data = result.to_dict()
    # Attach honest gas comparison
    gas_report = calculate_theoretical_gas_comparison(len(manifest.actions))
    response_data["gas_analysis"] = gas_report.to_dict()

    return response_data


@app.post("/api/gas-analysis")
async def compute_gas_metrics(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Compute honest gas breakdown and step reduction metrics."""
    action_count = payload.get("action_count")
    if not isinstance(action_count, int) or action_count < 1:
        raise HTTPException(status_code=422, detail="action_count must be an integer >= 1.")

    report = calculate_theoretical_gas_comparison(action_count)
    return report.to_dict()


# Serve frontend static assets if directory exists
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
