import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

TERMINAL_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 48px; background: #070a12;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    display: flex; justify-content: center; align-items: center;
    height: 100vh;
  }
  .window {
    width: 100%; height: 100%; background: #0b1120;
    border-radius: 14px; border: 1px solid #1e293b;
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.85);
    display: flex; flex-direction: column; overflow: hidden;
  }
  .header {
    background: #0f172a; padding: 16px 24px;
    display: flex; align-items: center; gap: 10px;
    border-bottom: 1px solid #1e293b;
  }
  .dot { width: 14px; height: 14px; border-radius: 50%; }
  .red { background: #ef4444; } .yellow { background: #f59e0b; } .green { background: #10b981; }
  .title { color: #94a3b8; font-size: 15px; margin-left: 14px; letter-spacing: 0.5px; }
  #terminal {
    padding: 32px 36px; color: #e2e8f0; font-size: 19px;
    line-height: 1.6; overflow-y: auto; flex: 1; white-space: pre-wrap;
  }
  .prompt { color: #38bdf8; font-weight: 600; }
  .cmd { color: #f8fafc; font-weight: 600; }
  .cursor { display: inline-block; width: 10px; height: 22px; background: #38bdf8; vertical-align: middle; animation: blink 1s infinite; margin-left: 4px; }
  @keyframes blink { 50% { opacity: 0; } }
  .output-line { margin: 2px 0; }
  .text-success { color: #4ade80; }
  .text-danger { color: #f87171; }
  .text-cyan { color: #38bdf8; }
  .text-dim { color: #94a3b8; }
</style>
</head>
<body>
  <div class="window">
    <div class="header">
      <div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
      <span class="title">JimmyOgb@pharos-atlantic: ~/pharos-batch-executor</span>
    </div>
    <div id="terminal"></div>
  </div>
  <script>
    const term = document.getElementById('terminal');
    window.startCommand = (promptText = 'JimmyOgb@atlantic:~/pharos-batch-executor$ ') => {
      const line = document.createElement('div');
      line.className = 'command-line';
      line.innerHTML = '<span class="prompt">' + promptText + '</span><span class="cmd"></span><span class="cursor"></span>';
      term.appendChild(line);
      term.scrollTop = term.scrollHeight;
    };
    window.typeChar = (ch) => {
      const cmds = document.querySelectorAll('.cmd');
      if (cmds.length) {
        cmds[cmds.length - 1].textContent += ch;
        term.scrollTop = term.scrollHeight;
      }
    };
    window.finishCommand = () => {
      const cursors = document.querySelectorAll('.cursor');
      if (cursors.length) cursors[cursors.length - 1].remove();
    };
    window.appendOutput = (text) => {
      const out = document.createElement('div');
      out.className = 'output-line';
      if (text.includes('SUCCESS') || text.includes('PASSED') || text.includes('PASS') || text.includes('Verified')) {
        out.className += ' text-success';
      } else if (text.includes('FAILED') || text.includes('revert') || text.includes('Reverted')) {
        out.className += ' text-danger';
      } else if (text.includes('Chain ID') || text.includes('MultiCall3')) {
        out.className += ' text-cyan';
      } else {
        out.className += ' text-dim';
      }
      out.textContent = text;
      term.appendChild(out);
      term.scrollTop = term.scrollHeight;
    };
  </script>
</body>
</html>
"""

CURSOR_JS = """
() => {
  if (document.getElementById('demo-cursor')) return;
  const cursor = document.createElement('div');
  cursor.id = 'demo-cursor';
  Object.assign(cursor.style, {
    position: 'fixed', top: '0px', left: '0px',
    width: '24px', height: '24px',
    background: 'rgba(56, 189, 248, 0.9)',
    border: '2px solid white', borderRadius: '50%',
    boxShadow: '0 0 16px rgba(56, 189, 248, 0.8)',
    pointerEvents: 'none', zIndex: '999999',
    transition: 'transform 0.25s cubic-bezier(0.22, 1, 0.36, 1)',
    transform: 'translate(-50%, -50%)'
  });
  document.body.appendChild(cursor);

  document.addEventListener('mousemove', e => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
  });
  document.addEventListener('mousedown', e => {
    cursor.style.transform = 'translate(-50%, -50%) scale(0.7)';
    const ripple = document.createElement('div');
    Object.assign(ripple.style, {
      position: 'fixed', left: e.clientX + 'px', top: e.clientY + 'px',
      width: '12px', height: '12px', borderRadius: '50%',
      border: '2px solid rgba(56, 189, 248, 0.95)',
      transform: 'translate(-50%, -50%) scale(1)',
      opacity: '1', pointerEvents: 'none', zIndex: '999998',
      transition: 'all 0.45s ease-out'
    });
    document.body.appendChild(ripple);
    requestAnimationFrame(() => {
      ripple.style.transform = 'translate(-50%, -50%) scale(4)';
      ripple.style.opacity = '0';
    });
    setTimeout(() => ripple.remove(), 450);
  });
  document.addEventListener('mouseup', () => {
    cursor.style.transform = 'translate(-50%, -50%) scale(1)';
  });
}
"""

async def smooth_move(page, target_x: float, target_y: float, steps: int = 25):
    await page.mouse.move(target_x, target_y, steps=steps)

async def smooth_click(page, selector: str, pause_after: float = 1.2):
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=10000)
    await loc.scroll_into_view_if_needed()
    box = await loc.bounding_box()
    if box:
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        await page.mouse.move(target_x, target_y, steps=25)
        await asyncio.sleep(0.25)
        await page.mouse.click(target_x, target_y)
    else:
        await loc.click()
    await asyncio.sleep(pause_after)

async def run_live_cli_command(page, command: str, cwd: str, pause_after: float = 2.0):
    await page.evaluate("window.startCommand()")
    for ch in command:
        await page.evaluate(f"window.typeChar({repr(ch)})")
        await asyncio.sleep(0.04)
    await asyncio.sleep(0.3)
    await page.evaluate("window.finishCommand()")

    env = os.environ.copy()
    env["PYTHONPATH"] = cwd
    proc = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, env=env
    )
    for line in proc.stdout:
        clean_line = line.rstrip()
        await page.evaluate(f"window.appendOutput({repr(clean_line)})")
        await asyncio.sleep(0.05)
    proc.wait()
    await asyncio.sleep(pause_after)

async def record_demo(workspace_dir: str):
    raw_video_dir = os.path.join(workspace_dir, "raw_video")
    os.makedirs(raw_video_dir, exist_ok=True)

    # 1. Start backend server
    print("Starting FastAPI backend on port 8899...")
    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = workspace_dir
    server_proc = subprocess.Popen(
        ["python", "cli.py", "serve", "--port", "8899"],
        cwd=workspace_dir,
        env=server_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server readiness
    for _ in range(20):
        try:
            res = subprocess.run(
                ["curl.exe", "-s", "http://127.0.0.1:8899/api/status"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0 and "chain_id" in res.stdout:
                print("Server is up and connected to Atlantic node!")
                break
        except Exception:
            pass
        time.sleep(0.5)

    try:
        async with async_playwright() as p:
            print("Launching Chromium at 1920x1080...")
            browser = await p.chromium.launch(
                headless=True,
                args=["--window-size=1920,1080", "--disable-gpu"]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=raw_video_dir,
                record_video_size={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            # --- SCENE 1: Terminal CLI (0s to ~35s) ---
            print("Scene 1: Terminal CLI demonstration...")
            await page.set_content(TERMINAL_HTML)
            await asyncio.sleep(2.5)

            # Command 1: status
            print("Typing and running `python cli.py status`...")
            await run_live_cli_command(page, "python cli.py status", workspace_dir, pause_after=3.5)

            # Command 2: run partial failure
            print("Typing and running `python cli.py run manifests/atlantic_partial_failure.json`...")
            await run_live_cli_command(page, "python cli.py run manifests/atlantic_partial_failure.json", workspace_dir, pause_after=4.5)

            # --- SCENE 2: Web Dashboard Walkthrough (35s to ~95s) ---
            print("Scene 2: Web Dashboard demonstration...")
            await page.goto("http://127.0.0.1:8899", wait_until="networkidle")
            await page.evaluate(CURSOR_JS)
            await asyncio.sleep(2.0)

            # Inspect Header & Network Pill
            await page.mouse.move(960, 45, steps=30)
            await asyncio.sleep(1.0)
            await page.mouse.move(1750, 45, steps=30)
            await asyncio.sleep(1.5)

            # Inspect Status Bar
            await page.mouse.move(400, 110, steps=25)
            await asyncio.sleep(1.0)
            await page.mouse.move(800, 110, steps=25)
            await asyncio.sleep(1.0)
            await page.mouse.move(1550, 110, steps=25)
            await asyncio.sleep(1.5)

            # 1. Select Account Inspection scenario
            print("Selecting Account Inspection scenario...")
            await smooth_click(page, "#btn-scenario-account", pause_after=2.0)

            # Click Execute
            print("Clicking Execute Single MultiCall3 Batch (Account Inspection)...")
            await smooth_click(page, "#btn-execute-batch", pause_after=4.0)

            # Move cursor to summary stats
            await smooth_move(page, 1300, 220, steps=25)
            await asyncio.sleep(2.0)

            # 2. Select Partial Failure scenario
            print("Selecting Partial Failure scenario...")
            await smooth_click(page, "#btn-scenario-partial", pause_after=2.0)

            # Click Execute
            print("Clicking Execute Single MultiCall3 Batch (Partial Failure)...")
            await smooth_click(page, "#btn-execute-batch", pause_after=4.0)

            # Inspect results summary (2 succeeded, 1 reverted)
            await smooth_move(page, 1400, 220, steps=25)
            await asyncio.sleep(2.0)

            # Scroll down to action results and highlight Action 2 failure
            print("Inspecting Action 2 partial failure and decoded revert...")
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(1.0)
            await smooth_move(page, 1400, 450, steps=30)
            await asyncio.sleep(3.0)

            # Expand collapsible raw inspector
            print("Expanding Raw Calldata & Node Response Inspector...")
            await smooth_click(page, "summary", pause_after=1.5)
            await page.mouse.wheel(0, 350)
            await asyncio.sleep(1.0)
            await smooth_move(page, 1400, 680, steps=25)
            await asyncio.sleep(2.5)

            # Scroll to Honest Gas Comparison
            print("Highlighting Honest Gas Analysis...")
            await smooth_move(page, 1400, 850, steps=25)
            await asyncio.sleep(3.0)

            # Final concluding pause
            print("Finalizing recording...")
            await asyncio.sleep(4.0)

            video_path = await page.video.path()
            await context.close()
            await browser.close()
            print(f"Raw video recorded at: {video_path}")
            return video_path
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    print(f"Merging {video_path} + {audio_path} -> {output_path}...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr)
        raise RuntimeError("FFmpeg merge failed")
    print("Merge complete!")

if __name__ == "__main__":
    WORKSPACE = r"C:\Users\NO GO NO\PharosBuild\skills\pharos-batch-executor"
    raw_video = asyncio.run(record_demo(WORKSPACE))
    voiceover = os.path.join(WORKSPACE, "voiceover.mp3")
    output_mp4 = os.path.join(WORKSPACE, "pharos_batch_executor_demo.mp4")
    merge_audio_video(raw_video, voiceover, output_mp4)
