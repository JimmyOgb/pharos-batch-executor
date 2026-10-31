import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROD_URL = "https://pharos-batch-executor.vercel.app"

async def verify():
    console_logs = []
    page_errors = []
    network_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("request", lambda req: network_requests.append((req.method, req.url)))

        print(f"Navigating to {PROD_URL}...")
        resp = await page.goto(PROD_URL, wait_until="networkidle")
        print(f"HTTP Status: {resp.status}")
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # 1. Verify Status Bar
        await page.wait_for_selector("#stat-block")
        await asyncio.sleep(2.0)
        block_text = await page.locator("#stat-block").text_content()
        net_text = await page.locator("#network-status-text").text_content()
        chain_text = await page.locator("#stat-chain").text_content()
        multicall_text = await page.locator("#stat-multicall").text_content()

        print(f"Network Status: {net_text}")
        print(f"Live Block Height: {block_text}")
        print(f"Chain ID: {chain_text}")
        print(f"MultiCall3 Address: {multicall_text}")

        assert "688689" in chain_text, "Chain ID must contain 688689"
        assert "#" in block_text, "Block height must be populated"

        # 2. Test Execution: Account Inspection Scenario
        print("Clicking Execute Single MultiCall3 Batch (Account Inspection)...")
        await page.click("#btn-execute-batch")
        await page.wait_for_selector("#results-status-badge")
        await asyncio.sleep(3.0)

        badge_account = await page.locator("#results-status-badge").text_content()
        total_account = await page.locator("#res-total").text_content()
        success_account = await page.locator("#res-success").text_content()
        failed_account = await page.locator("#res-failed").text_content()
        print(f"Account Execution -> Status: {badge_account}, Total: {total_account}, Success: {success_account}, Failed: {failed_account}")
        assert total_account == "3" and success_account == "3", "Account batch should have 3 successes"

        # 3. Test Execution: Partial Failure Scenario
        print("Selecting Partial Failure scenario...")
        await page.click("#btn-scenario-partial")
        await asyncio.sleep(1.0)
        print("Clicking Execute Single MultiCall3 Batch (Partial Failure)...")
        await page.click("#btn-execute-batch")
        await asyncio.sleep(3.0)

        badge_partial = await page.locator("#results-status-badge").text_content()
        total_partial = await page.locator("#res-total").text_content()
        success_partial = await page.locator("#res-success").text_content()
        failed_partial = await page.locator("#res-failed").text_content()
        print(f"Partial Execution -> Status: {badge_partial}, Total: {total_partial}, Success: {success_partial}, Failed: {failed_partial}")
        assert total_partial == "3" and success_partial == "2" and failed_partial == "1", "Partial failure batch must show 2 successes, 1 failed"

        # Verify decoded revert reason in DOM
        revert_text = await page.locator(".revert-msg").first.text_content()
        print(f"Decoded Revert Text: {revert_text}")
        assert "ERC20: transfer amount exceeds allowance" in revert_text, "Must decode OpenZeppelin revert reason"

        # 4. Verify Gas Card
        gas_avoided = await page.locator("#gas-overhead-saved").text_content()
        print(f"Gas Overhead Avoided: {gas_avoided}")
        assert "42,000" in gas_avoided, "Must display 42,000 gas units avoided"

        # 5. Capture screenshot of production verification
        screenshot_path = "screenshots/vercel_production_verification.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Production screenshot captured to: {screenshot_path}")

        # 6. Verify RPC Network Requests
        rpc_requests = [r for r in network_requests if "atlantic.dplabs-internal.com" in r[1]]
        print(f"Total Browser-originated requests to Atlantic RPC: {len(rpc_requests)}")
        assert len(rpc_requests) >= 2, "Browser must make direct JSON-RPC POST requests to Atlantic node"

        print(f"Console errors: {len(page_errors)}")
        for err in page_errors:
            print("ERROR:", err)
        assert len(page_errors) == 0, "No uncaught JavaScript errors allowed"

        await browser.close()
        print("VERIFICATION COMPLETE: ALL CHECKS PASSED!")

if __name__ == "__main__":
    asyncio.run(verify())
