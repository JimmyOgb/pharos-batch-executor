// Pharos Batch Executor Web Client
// Interacts with Pharos Atlantic Testnet (Chain ID 688689)
// Dual-mode: Uses local backend API if available, falls back to direct browser-originated JSON-RPC

const ATLANTIC_RPC_URL = "https://atlantic.dplabs-internal.com";
const EXPECTED_CHAIN_ID = 688689;
const MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11";
const USDC_ADDRESS = "0xad58e5d48259d57a220c8db4630aeb29cb01584c";
const WPHRS_ADDRESS = "0x16b60700abb790EF7d4a413A28E51048b61e2A66";
const REWARD_WALLET = "0xcc8475078f3C13975AcaA72F2B824097551Ca768";

// Pre-configured Verified Scenarios
const SCENARIOS = {
  account: {
    title: "Atlantic Account & Block Inspection",
    require_success: false,
    actions: [
      {
        target: MULTICALL3_ADDRESS,
        call_data: "0x42cbb15c",
        description: "MultiCall3.getBlockNumber()",
        action_type: "read",
        expected_result_type: "uint256"
      },
      {
        target: MULTICALL3_ADDRESS,
        call_data: "0x0e5d8001",
        description: "MultiCall3.getCurrentBlockTimestamp()",
        action_type: "read",
        expected_result_type: "uint256"
      },
      {
        target: MULTICALL3_ADDRESS,
        call_data: "0x4d2301cc000000000000000000000000cc8475078f3c13975acaa72f2b824097551ca768",
        description: `MultiCall3.getEthBalance(${REWARD_WALLET.slice(0, 6)}...${REWARD_WALLET.slice(-4)})`,
        action_type: "read",
        expected_result_type: "uint256"
      }
    ]
  },
  partial: {
    title: "Atlantic Partial Failure Isolation",
    require_success: false,
    actions: [
      {
        target: MULTICALL3_ADDRESS,
        call_data: "0x42cbb15c",
        description: "MultiCall3.getBlockNumber() [Valid]",
        action_type: "read",
        expected_result_type: "uint256"
      },
      {
        target: USDC_ADDRESS,
        call_data: "0x23b872dd0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000f4240",
        description: "USDC.transferFrom without allowance [Deliberate Revert]",
        action_type: "read",
        expected_result_type: null
      },
      {
        target: MULTICALL3_ADDRESS,
        call_data: "0x0e5d8001",
        description: "MultiCall3.getCurrentBlockTimestamp() [Valid]",
        action_type: "read",
        expected_result_type: "uint256"
      }
    ]
  },
  token: {
    title: "Atlantic Token Registry Inspection",
    require_success: false,
    actions: [
      {
        target: WPHRS_ADDRESS,
        call_data: "0x95d89b41",
        description: "WPHRS.symbol()",
        action_type: "read",
        expected_result_type: "string"
      },
      {
        target: USDC_ADDRESS,
        call_data: "0x95d89b41",
        description: "USDC.symbol()",
        action_type: "read",
        expected_result_type: "string"
      },
      {
        target: USDC_ADDRESS,
        call_data: "0x313ce567",
        description: "USDC.decimals()",
        action_type: "read",
        expected_result_type: "uint8"
      }
    ]
  }
};

let currentManifest = JSON.parse(JSON.stringify(SCENARIOS.account));

// DOM Elements
const networkPill = document.getElementById("network-pill");
const networkStatusText = document.getElementById("network-status-text");
const statBlock = document.getElementById("stat-block");
const actionCountBadge = document.getElementById("action-count-badge");
const actionsList = document.getElementById("actions-list");
const requireSuccessToggle = document.getElementById("require-success-toggle");
const btnExecute = document.getElementById("btn-execute-batch");
const resultsStatusBadge = document.getElementById("results-status-badge");

const resTotal = document.getElementById("res-total");
const resSuccess = document.getElementById("res-success");
const resFailed = document.getElementById("res-failed");
const resBlockNum = document.getElementById("res-block-num");
const resultsList = document.getElementById("results-list");

const gasStandaloneCount = document.getElementById("gas-standalone-count");
const gasBatchedCount = document.getElementById("gas-batched-count");
const gasStepsEliminated = document.getElementById("gas-steps-eliminated");
const gasOverheadSaved = document.getElementById("gas-overhead-saved");

const inspectCalldata = document.getElementById("inspect-calldata");
const inspectResponse = document.getElementById("inspect-response");

// Direct Browser JSON-RPC Helper
async function browserRpcCall(method, params = []) {
  const resp = await fetch(ATLANTIC_RPC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params })
  });
  if (!resp.ok) throw new Error(`Atlantic RPC transport HTTP ${resp.status}`);
  const data = await resp.json();
  if (data.error) throw new Error(data.error.message || "Atlantic RPC returned an error");
  return data.result;
}

// ABI Encoder for tryAggregate(bool, (address,bytes)[])
function encodeTryAggregate(requireSuccess, actions) {
  let res = "0xbce38bd7";
  res += requireSuccess
    ? "0000000000000000000000000000000000000000000000000000000000000001"
    : "0000000000000000000000000000000000000000000000000000000000000000";
  res += "0000000000000000000000000000000000000000000000000000000000000040";
  const n = actions.length;
  res += n.toString(16).padStart(64, "0");
  const tupleHeads = [];
  const tupleTails = [];
  let currentTailOffset = n * 32;

  for (const act of actions) {
    tupleHeads.push(currentTailOffset.toString(16).padStart(64, "0"));
    const tgt = act.target.toLowerCase().replace("0x", "").padStart(64, "0");
    const cdHex = act.call_data.toLowerCase().replace("0x", "");
    const cdBytesLen = Math.floor(cdHex.length / 2);
    const paddedCd = cdHex.padEnd(Math.ceil(cdHex.length / 64) * 64, "0");
    const tData = tgt + "0000000000000000000000000000000000000000000000000000000000000040" + cdBytesLen.toString(16).padStart(64, "0") + paddedCd;
    tupleTails.push(tData);
    currentTailOffset += Math.floor(tData.length / 2);
  }

  res += tupleHeads.join("") + tupleTails.join("");
  return res;
}

// ABI Decoder for tryAggregate result: (bool, bytes)[]
function decodeTryAggregate(rawHex) {
  const data = rawHex.replace("0x", "");
  const arrOffset = parseInt(data.slice(0, 64), 16) * 2;
  const count = parseInt(data.slice(arrOffset, arrOffset + 64), 16);
  const payloadStart = arrOffset + 64;
  const results = [];

  for (let i = 0; i < count; i++) {
    const elemRelOffset = parseInt(data.slice(payloadStart + i * 64, payloadStart + (i + 1) * 64), 16) * 2;
    const elemStart = payloadStart + elemRelOffset;
    const success = parseInt(data.slice(elemStart, elemStart + 64), 16) !== 0;
    const bytesRelOffset = parseInt(data.slice(elemStart + 64, elemStart + 128), 16) * 2;
    const bytesStart = elemStart + bytesRelOffset;
    const bytesLen = parseInt(data.slice(bytesStart, bytesStart + 64), 16);
    const rawBytesHex = data.slice(bytesStart + 64, bytesStart + 64 + bytesLen * 2);

    let revertReason = null;
    let decodedValue = null;

    if (!success) {
      if (rawBytesHex.startsWith("08c379a0")) {
        const sLen = parseInt(rawBytesHex.slice(8 + 64, 8 + 128), 16);
        const sHex = rawBytesHex.slice(8 + 128, 8 + 128 + sLen * 2);
        try {
          revertReason = decodeHexUTF8(sHex);
        } catch {
          revertReason = "Reverted with Error(string)";
        }
      } else if (rawBytesHex.startsWith("4e487b71")) {
        const panicCode = parseInt(rawBytesHex.slice(8, 72), 16);
        revertReason = `Panic(0x${panicCode.toString(16)})`;
      } else {
        revertReason = rawBytesHex.length > 0 ? `Custom error: 0x${rawBytesHex.slice(0, 8)}` : "Transaction reverted silently";
      }
    } else {
      if (rawBytesHex.length === 64) {
        decodedValue = BigInt("0x" + rawBytesHex).toString();
      }
    }

    results.append ? null : results.push({
      success,
      return_data: "0x" + rawBytesHex,
      revert_reason: revertReason,
      decoded_value: decodedValue
    });
  }

  return results;
}

function decodeHexUTF8(hex) {
  let str = "";
  for (let i = 0; i < hex.length; i += 2) {
    str += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
  }
  return str;
}

// Fetch Live Network Status on Load
async function fetchStatus() {
  try {
    // 1. Try local backend
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        statBlock.textContent = `#${data.network.block_number.toLocaleString()}`;
        networkStatusText.textContent = "Atlantic Testnet (Connected)";
        networkPill.className = "network-badge live";
        return;
      }
    } catch {
      // fallback to browser RPC
    }

    // 2. Browser Direct RPC
    const chainHex = await browserRpcCall("eth_chainId");
    const chainId = parseInt(chainHex, 16);
    if (chainId !== EXPECTED_CHAIN_ID) {
      throw new Error(`Unexpected Chain ID: ${chainId} (expected ${EXPECTED_CHAIN_ID})`);
    }

    const blockHex = await browserRpcCall("eth_blockNumber");
    const blockNum = parseInt(blockHex, 16);
    statBlock.textContent = `#${blockNum.toLocaleString()}`;
    networkStatusText.textContent = "Atlantic Testnet (Direct RPC)";
    networkPill.className = "network-badge live";
  } catch (err) {
    networkStatusText.textContent = "Atlantic Node Offline / Error";
    networkPill.className = "network-badge";
    statBlock.textContent = "Unavailable";
    console.error("Status fetch failed:", err);
  }
}

// Render Actions List in Manifest Panel
function renderActions() {
  actionsList.innerHTML = "";
  actionCountBadge.textContent = `${currentManifest.actions.length} Actions Configured`;

  currentManifest.actions.forEach((act, idx) => {
    const row = document.createElement("div");
    row.className = "action-row";
    row.innerHTML = `
      <div class="action-row-head">
        <span class="action-idx">Action #${idx + 1}</span>
        <span class="action-desc">${act.description || "Custom Call"}</span>
      </div>
      <div class="action-row-body">
        <div class="action-param">
          <span class="k">Target Contract:</span>
          <span class="v" title="${act.target}">${act.target.slice(0, 10)}...${act.target.slice(-8)}</span>
        </div>
        <div class="action-param">
          <span class="k">Selector / Calldata:</span>
          <span class="v" title="${act.call_data}">${act.call_data.length > 20 ? act.call_data.slice(0, 18) + "..." : act.call_data}</span>
        </div>
      </div>
    `;
    actionsList.appendChild(row);
  });

  updateGasEstimatePreview(currentManifest.actions.length);
}

// Update Gas Estimate Metrics for Action Count
function updateGasEstimatePreview(count) {
  gasStandaloneCount.textContent = `${count} transactions`;
  gasBatchedCount.textContent = "1 transaction";
  gasStepsEliminated.textContent = `${count - 1} steps saved`;
  const overheadAvoided = (count - 1) * 21000;
  gasOverheadSaved.textContent = `${overheadAvoided.toLocaleString()} gas units`;
}

// Select Pre-configured Scenario
function selectScenario(scenarioKey) {
  document.querySelectorAll(".scenario-buttons button").forEach(b => b.classList.remove("active"));
  document.getElementById(`btn-scenario-${scenarioKey}`).classList.add("active");
  currentManifest = JSON.parse(JSON.stringify(SCENARIOS[scenarioKey]));
  requireSuccessToggle.checked = currentManifest.require_success;
  renderActions();
}

// Execute Batch through Backend API or Direct Browser RPC
async function executeBatch() {
  btnExecute.disabled = true;
  btnExecute.textContent = "Dispatching MultiCall3 eth_call...";
  resultsStatusBadge.textContent = "Processing...";
  resultsStatusBadge.className = "badge";

  try {
    currentManifest.require_success = requireSuccessToggle.checked;

    let data = null;

    // 1. Try local backend first
    try {
      const res = await fetch("/api/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentManifest)
      });
      if (res.ok) {
        data = await res.json();
      }
    } catch {
      // local backend not reachable, proceed to browser RPC
    }

    // 2. Direct Browser-originated MultiCall3 eth_call
    if (!data) {
      const calldata = encodeTryAggregate(currentManifest.require_success, currentManifest.actions);
      const rawHex = await browserRpcCall("eth_call", [
        { to: MULTICALL3_ADDRESS, data: calldata },
        "latest"
      ]);
      const blockHex = await browserRpcCall("eth_blockNumber");
      const blockNum = parseInt(blockHex, 16);

      const decodedResults = decodeTryAggregate(rawHex);

      let successCount = 0;
      let failCount = 0;
      const resultsWithActions = decodedResults.map((r, idx) => {
        if (r.success) successCount++;
        else failCount++;
        const act = currentManifest.actions[idx] || {};
        return {
          index: idx,
          target: act.target || MULTICALL3_ADDRESS,
          description: act.description || `Action #${idx + 1}`,
          success: r.success,
          return_data: r.return_data,
          revert_reason: r.revert_reason,
          decoded_value: r.decoded_value
        };
      });

      data = {
        network: {
          name: "Pharos Atlantic Testnet",
          chain_id: EXPECTED_CHAIN_ID,
          block_number: blockNum,
          multicall3_address: MULTICALL3_ADDRESS
        },
        calldata_sent: calldata,
        raw_rpc_response: rawHex,
        summary: {
          total_actions: currentManifest.actions.length,
          successful_actions: successCount,
          failed_actions: failCount,
          all_succeeded: failCount === 0
        },
        results: resultsWithActions
      };
    }

    renderResults(data);
  } catch (err) {
    resultsStatusBadge.textContent = "Execution Failed";
    resultsStatusBadge.className = "badge badge-warning";
    resultsList.innerHTML = `
      <div class="result-item revert">
        <div class="result-head">
          <span class="result-title">Error</span>
          <span class="result-tag tag-revert">FAILED</span>
        </div>
        <div class="revert-msg">${err.message}</div>
      </div>
    `;
  } finally {
    btnExecute.disabled = false;
    btnExecute.textContent = "Execute Single MultiCall3 Batch";
    fetchStatus();
  }
}

// Render Results Received from Node
function renderResults(data) {
  const summary = data.summary;
  resTotal.textContent = summary.total_actions;
  resSuccess.textContent = summary.successful_actions;
  resFailed.textContent = summary.failed_actions;
  resBlockNum.textContent = `#${data.network.block_number.toLocaleString()}`;

  if (summary.all_succeeded) {
    resultsStatusBadge.textContent = "All Succeeded";
    resultsStatusBadge.className = "badge-success";
  } else {
    resultsStatusBadge.textContent = `Partial Success (${summary.successful_actions}/${summary.total_actions})`;
    resultsStatusBadge.className = "badge-warning";
  }

  // Populate inspector
  inspectCalldata.textContent = data.calldata_sent;
  inspectResponse.textContent = data.raw_rpc_response;

  // Render per-action items
  resultsList.innerHTML = "";
  data.results.forEach((r, idx) => {
    const item = document.createElement("div");
    item.className = `result-item ${r.success ? "success" : "revert"}`;
    item.innerHTML = `
      <div class="result-head">
        <span class="result-title">Action #${idx + 1}: ${r.description}</span>
        <span class="result-tag ${r.success ? "tag-success" : "tag-revert"}">
          ${r.success ? "SUCCESS" : "FAILED"}
        </span>
      </div>
      ${r.success
        ? `<div class="result-return-data" title="${r.return_data}">
             <strong>Return Data:</strong> <code>${r.return_data.length > 34 ? r.return_data.slice(0, 32) + "..." : r.return_data}</code>
             ${r.decoded_value ? `<span class="decoded-val">(Value: ${Number(r.decoded_value).toLocaleString()})</span>` : ""}
           </div>`
        : `<div class="revert-msg">
             <strong>Decoded Revert Reason:</strong> ${r.revert_reason || "Unknown Revert"}
           </div>`
      }
    `;
    resultsList.appendChild(item);
  });
}

// Add Custom Action Helper
function addActionPrompt() {
  const target = prompt("Target Contract Address (0x...):", MULTICALL3_ADDRESS);
  if (!target || !target.startsWith("0x") || target.length !== 42) {
    if (target) alert("Invalid target address format.");
    return;
  }
  const callData = prompt("Calldata (0x...):", "0x42cbb15c");
  if (!callData || !callData.startsWith("0x")) {
    if (callData) alert("Invalid calldata format.");
    return;
  }
  const desc = prompt("Action Description:", "Custom Query") || "Custom Query";

  currentManifest.actions.push({
    target,
    call_data: callData,
    description: desc,
    action_type: "read",
    expected_result_type: null
  });

  renderActions();
}

// Event Listeners
document.getElementById("btn-scenario-account").addEventListener("click", () => selectScenario("account"));
document.getElementById("btn-scenario-partial").addEventListener("click", () => selectScenario("partial"));
document.getElementById("btn-scenario-token").addEventListener("click", () => selectScenario("token"));
btnExecute.addEventListener("click", executeBatch);
document.getElementById("btn-add-action").addEventListener("click", addActionPrompt);

// Initialize
renderActions();
fetchStatus();
