"""Capture high-resolution screenshots of the running Pharos Batch Executor application."""

import os
import sys
import time
import shutil
import subprocess
from playwright.sync_api import sync_playwright

WORKSPACE = r"C:\Users\NO GO NO\PharosBuild\skills\pharos-batch-executor"
ARTIFACT_DIR = r"C:\Users\NO GO NO\.gemini\antigravity-cli\brain\3bdb2b58-610a-407d-930a-b65b31e19de6"
SCREENSHOT_DIR = os.path.join(WORKSPACE, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

PORT = 8899
SERVER_URL = f"http://127.0.0.1:{PORT}"

def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        res = subprocess.run(["curl.exe", "-s", f"{url}/api/status"], capture_output=True, text=True)
        if "chain_id" in res.stdout:
            return True
        time.sleep(0.5)
    return False

def main():
    print(f"Starting server on {SERVER_URL}...")
    env = dict(os.environ)
    env["PYTHONPATH"] = WORKSPACE
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "batch.server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=WORKSPACE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    try:
        if not wait_for_server(SERVER_URL):
            print("Server failed to start within timeout", file=sys.stderr)
            out, err = server_proc.communicate(timeout=3)
            print("Server STDOUT:", out.decode(), file=sys.stderr)
            print("Server STDERR:", err.decode(), file=sys.stderr)
            return 1

        print("Server is ready. Launching Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 950})

            # Navigate to Dashboard
            print(f"Navigating to {SERVER_URL}...")
            page.goto(SERVER_URL, wait_until="networkidle")

            # Wait for live block number to appear (e.g. #32,...)
            page.wait_for_selector("#stat-block:not(:has-text('Loading...'))", timeout=15000)
            time.sleep(1)

            # Screenshot 1: Loaded Dashboard
            shot1_path = os.path.join(SCREENSHOT_DIR, "batch_executor_dashboard_loaded.png")
            page.screenshot(path=shot1_path, full_page=True)
            print(f"Captured: {shot1_path}")

            # Click Scenario 2: Partial Failure
            print("Selecting Partial Failure scenario...")
            page.click("#btn-scenario-partial")
            time.sleep(0.5)

            # Click Execute Batch
            print("Clicking Execute Batch...")
            page.click("#btn-execute-batch")

            # Wait for execution results to populate
            page.wait_for_selector(".result-item.revert", timeout=20000)
            time.sleep(1)

            # Open raw details inspector
            page.click("details summary")
            time.sleep(0.5)

            # Screenshot 2: Executed Partial Failure
            shot2_path = os.path.join(SCREENSHOT_DIR, "batch_executor_partial_failure_executed.png")
            page.screenshot(path=shot2_path, full_page=True)
            print(f"Captured: {shot2_path}")

            browser.close()

            # Copy to artifact dir for markdown rendering
            shutil.copy(shot1_path, os.path.join(ARTIFACT_DIR, "batch_executor_dashboard_loaded.png"))
            shutil.copy(shot2_path, os.path.join(ARTIFACT_DIR, "batch_executor_partial_failure_executed.png"))
            print("Screenshots successfully copied to artifact directory.")

    finally:
        print("Stopping server...")
        server_proc.terminate()
        server_proc.wait()
        print("Done.")

if __name__ == "__main__":
    sys.exit(main())
