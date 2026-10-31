"""Live JSON-RPC transport and MultiCall3 execution client for Pharos Atlantic Testnet."""

import json
import time
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from batch.config import (
    DEFAULT_RPC_URL,
    CHAIN_ID,
    CHAIN_ID_HEX,
    MULTICALL3_ADDRESS,
    NETWORK_NAME
)
from batch.manifest import BatchManifest
from batch.encoding import encode_try_aggregate, encode_aggregate3
from batch.decoder import decode_try_aggregate_return, BatchExecutionReport


class NetworkRPCError(Exception):
    """Raised when an RPC request fails or the node returns an error."""
    pass


@dataclass
class LiveBatchExecutionResult:
    """Combines on-chain execution report with live node metadata."""
    report: BatchExecutionReport
    chain_id: int
    chain_id_hex: str
    block_number: int
    rpc_endpoint: str
    execution_timestamp: float
    raw_rpc_response: str
    calldata_sent: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for UI and API consumption."""
        return {
            "network": {
                "name": NETWORK_NAME,
                "chain_id": self.chain_id,
                "chain_id_hex": self.chain_id_hex,
                "rpc_endpoint": self.rpc_endpoint,
                "block_number": self.block_number,
                "timestamp": self.execution_timestamp,
            },
            "calldata_sent": self.calldata_sent,
            "raw_rpc_response": self.raw_rpc_response,
            "summary": {
                "total_actions": self.report.total_actions,
                "successful_actions": self.report.successful_actions,
                "failed_actions": self.report.failed_actions,
                "all_succeeded": self.report.all_succeeded,
            },
            "results": [
                {
                    "action_index": r.action_index,
                    "success": r.success,
                    "raw_return_data": r.raw_return_data,
                    "decoded_value": str(r.decoded_value) if r.decoded_value is not None else None,
                    "is_revert": r.is_revert,
                    "revert_type": r.revert_type,
                    "revert_message": r.revert_message,
                    "revert_code": r.revert_code,
                }
                for r in self.report.results
            ]
        }


class PharosBatchClient:
    """Client for querying Pharos Atlantic Testnet via JSON-RPC."""

    def __init__(self, rpc_url: str = DEFAULT_RPC_URL, timeout: float = 10.0):
        self.rpc_url = rpc_url
        self.timeout = timeout
        self.user_agent = "PharosBatchExecutor/0.1.0"

    def _rpc_call_urllib(self, method: str, params: List[Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": int(time.time() * 1000) % 1000000
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.rpc_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": self.user_agent
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp_text = resp.read().decode("utf-8")
            res = json.loads(resp_text)
            if "error" in res:
                err = res["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                raise NetworkRPCError(f"RPC Error for {method}: {msg}")
            return res.get("result")

    def _rpc_call_curl(self, method: str, params: List[Any]) -> Any:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": int(time.time() * 1000) % 1000000
        })
        cmd = [
            "curl.exe",
            "-s",
            "--max-time", str(int(self.timeout)),
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", payload,
            self.rpc_url
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 2)
        if proc.returncode != 0:
            raise NetworkRPCError(f"Curl fallback failed: {proc.stderr}")
        try:
            res = json.loads(proc.stdout)
        except Exception as e:
            raise NetworkRPCError(f"Failed to parse JSON from curl response: {proc.stdout[:200]}")
        if "error" in res:
            err = res["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise NetworkRPCError(f"RPC Error for {method}: {msg}")
        return res.get("result")

    def _call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """Execute a raw JSON-RPC call against the live endpoint with dual transport."""
        if params is None:
            params = []
        try:
            return self._rpc_call_urllib(method, params)
        except (urllib.error.URLError, TimeoutError, OSError):
            # Fall back to curl.exe which handles Windows IPv4/IPv6 dual-stack resolution immediately
            try:
                return self._rpc_call_curl(method, params)
            except Exception as e:
                raise NetworkRPCError(f"Failed to query Pharos RPC ({self.rpc_url}): {e}")

    def get_chain_id(self) -> int:
        """Fetch chain ID and verify against expected Chain ID 688689."""
        hex_val = self._call("eth_chainId")
        val = int(hex_val, 16)
        if val != CHAIN_ID:
            raise NetworkRPCError(
                f"Chain ID mismatch! Connected node reports {val} ({hex_val}), but expected {CHAIN_ID} ({CHAIN_ID_HEX})."
            )
        return val

    def get_block_number(self) -> int:
        """Fetch current on-chain block number."""
        hex_val = self._call("eth_blockNumber")
        return int(hex_val, 16)

    def get_code(self, address: str) -> str:
        """Fetch deployed bytecode at an address."""
        return self._call("eth_getCode", [address, "latest"])

    def get_balance(self, address: str) -> int:
        """Fetch native token balance in wei."""
        hex_val = self._call("eth_getBalance", [address, "latest"])
        return int(hex_val, 16)

    def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        """Execute a read-only EVM call without mutating state."""
        return self._call("eth_call", [{"to": to, "data": data}, block])

    def execute_read_batch(
        self,
        manifest: BatchManifest,
        block: str = "latest"
    ) -> LiveBatchExecutionResult:
        """
        Execute a batch of read-only calls through MultiCall3.tryAggregate.
        Dispatches a single eth_call to the verified MultiCall3 contract.
        """
        manifest.validate()
        calldata = encode_try_aggregate(manifest)

        # 1. Fetch current live block number
        current_block = self.get_block_number()
        timestamp = time.time()

        # 2. Dispatch single eth_call to MultiCall3
        raw_result = self.eth_call(to=MULTICALL3_ADDRESS, data=calldata, block=block)

        # 3. Decode the return array
        expected_types = [a.expected_result_type for a in manifest.actions]
        report = decode_try_aggregate_return(raw_result, expected_types=expected_types)

        return LiveBatchExecutionResult(
            report=report,
            chain_id=CHAIN_ID,
            chain_id_hex=CHAIN_ID_HEX,
            block_number=current_block,
            rpc_endpoint=self.rpc_url,
            execution_timestamp=timestamp,
            raw_rpc_response=raw_result,
            calldata_sent=calldata
        )
