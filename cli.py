#!/usr/bin/env python3
"""CLI interface for Pharos Batch Executor on Pharos Atlantic Testnet."""

import argparse
import json
import sys
import os

from batch.config import (
    NETWORK_NAME,
    CHAIN_ID,
    CHAIN_ID_HEX,
    MULTICALL3_ADDRESS,
    DEFAULT_RPC_URL
)
from batch.client import PharosBatchClient, NetworkRPCError
from batch.manifest import BatchManifest, ManifestValidationError
from batch.gas_math import calculate_theoretical_gas_comparison


def cmd_status(args):
    """Check live on-chain status of Pharos Atlantic node and MultiCall3."""
    print("=" * 70)
    print("PHAROS ATLANTIC TESTNET -- LIVE NODE & MULTICALL3 STATUS")
    print("=" * 70)
    client = PharosBatchClient(rpc_url=args.rpc)
    try:
        cid = client.get_chain_id()
        block = client.get_block_number()
        code = client.get_code(MULTICALL3_ADDRESS)
        code_len = len(code)
        is_deployed = code_len > 2
        print(f"Network Name:       {NETWORK_NAME}")
        print(f"Chain ID:           {cid} ({CHAIN_ID_HEX}) [Verified: {cid == CHAIN_ID}]")
        print(f"RPC Endpoint:       {client.rpc_url}")
        print(f"Current Block:      {block:,}")
        print(f"MultiCall3 Address: {MULTICALL3_ADDRESS}")
        print(f"MultiCall3 Code:    {code_len} bytes [Deployed: {is_deployed}]")
        print("-" * 70)
        print("Status: LIVE & READY FOR READ-ONLY BATCHING")
    except Exception as e:
        print(f"ERROR querying node: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args):
    """Run a batch manifest from a JSON file against live Atlantic MultiCall3."""
    if not os.path.isfile(args.manifest):
        print(f"Error: Manifest file not found at '{args.manifest}'", file=sys.stderr)
        sys.exit(1)

    with open(args.manifest, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        manifest = BatchManifest.from_dict(data)
    except ManifestValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)

    client = PharosBatchClient(rpc_url=args.rpc)
    print("=" * 70)
    print(f"EXECUTING BATCH: {manifest.title}")
    print(f"Target MultiCall3: {MULTICALL3_ADDRESS}")
    print(f"Actions in Batch:  {len(manifest.actions)}")
    print("=" * 70)

    try:
        result = client.execute_read_batch(manifest)
    except Exception as e:
        print(f"Execution Error: {e}", file=sys.stderr)
        sys.exit(1)

    report = result.report
    print(f"Live Block Number:  {result.block_number:,}")
    print(f"Total Actions:      {report.total_actions}")
    print(f"Successful Actions: {report.successful_actions}")
    print(f"Failed Actions:     {report.failed_actions}")
    print(f"Batch Succeeded:    {report.all_succeeded}")
    print("-" * 70)
    print(report.summary_table())
    print("-" * 70)

    # Print Gas & Step Comparison
    gas_report = calculate_theoretical_gas_comparison(len(manifest.actions))
    print("GAS & STEP COMPARISON METRICS:")
    print(f"  Standalone Transactions:        {gas_report.standalone_transaction_count}")
    print(f"  Batched Transactions:           {gas_report.batched_transaction_count}")
    print(f"  Confirmation Steps Eliminated:  {gas_report.confirmation_steps_eliminated}")
    print(f"  Theoretical Overhead Avoided:   {gas_report.theoretical_intrinsic_gas_overhead_avoided:,} gas units")
    print(f"  Notice:                         {gas_report.notice}")


def cmd_estimate(args):
    """Compute deterministic theoretical gas comparison metrics."""
    manifest_path = args.manifest or args.manifest_file
    if args.count:
        count = args.count
    elif manifest_path:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = len(data.get("actions", []))
    else:
        print("Please provide a manifest path or --count N", file=sys.stderr)
        sys.exit(1)

    report = calculate_theoretical_gas_comparison(count)
    print(json.dumps(report.to_dict(), indent=2))


def cmd_serve(args):
    """Launch the FastAPI server for the web UI."""
    import uvicorn
    print(f"Starting Pharos Batch Executor server on http://{args.host}:{args.port}")
    uvicorn.run("batch.server:app", host=args.host, port=args.port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Pharos Batch Executor CLI")
    parser.add_argument("--rpc", default=DEFAULT_RPC_URL, help="Atlantic JSON-RPC URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Query live Atlantic node and MultiCall3 status")
    p_status.set_defaults(func=cmd_status)

    # run
    p_run = subparsers.add_parser("run", help="Execute a batch manifest against live Atlantic node")
    p_run.add_argument("manifest", help="Path to manifest JSON file")
    p_run.set_defaults(func=cmd_run)

    # estimate
    p_est = subparsers.add_parser("estimate", help="Compute theoretical gas metrics")
    p_est.add_argument("manifest_file", nargs="?", default=None, help="Path to manifest JSON file")
    p_est.add_argument("--count", type=int, help="Number of actions")
    p_est.add_argument("--manifest", help="Path to manifest JSON file")
    p_est.set_defaults(func=cmd_estimate)

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch web UI dashboard")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host to bind")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
