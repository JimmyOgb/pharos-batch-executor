// Pharos Batch Executor Web Client
// Interacts with backend API and Pharos Atlantic Testnet

const MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11";
const USDC_ADDRESS = "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B";
const WPHRS_ADDRESS = "0x838800b758277CC111B2d48Ab01e5E164f8E9471";
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
        call_data: "0x0f28c97d",
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
        call_data: "0x0f28c97d",
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

// Fetch Live Network Status on Load
async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    statBlock.textContent = `#${data.network.block_number.toLocaleString()}`;
    networkStatusText.textContent = "Atlantic Testnet (Connected)";
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

// Execute Batch through Backend API
async function executeBatch() {
  btnExecute.disabled = true;
  btnExecute.textContent = "Dispatching MultiCall3 eth_call...";
  resultsStatusBadge.textContent = "Processing...";
  resultsStatusBadge.className = "badge";

  try {
    currentManifest.require_success = requireSuccessToggle.checked;
    const res = await fetch("/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentManifest)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Server error: HTTP ${res.status}`);
    }

    const data = await res.json();
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
    fetchStatus(); // refresh block number
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
    const desc = currentManifest.actions[idx]?.description || `Action #${idx + 1}`;

    if (r.success) {
      item.innerHTML = `
        <div class="result-head">
          <span class="result-title">Action #${idx + 1}: ${desc}</span>
          <span class="result-tag tag-success">SUCCESS</span>
        </div>
        <div class="result-detail">
          Decoded Return: <strong style="color: var(--text-main); font-family: var(--font-mono);">${r.decoded_value}</strong>
        </div>
        <div class="result-detail" style="font-family: var(--font-mono); font-size: 10px; color: var(--text-dim);">
          Raw Hex: ${r.raw_return_data}
        </div>
      `;
    } else {
      item.innerHTML = `
        <div class="result-head">
          <span class="result-title">Action #${idx + 1}: ${desc}</span>
          <span class="result-tag tag-revert">REVERTED [${r.revert_type || "Error"}]</span>
        </div>
        <div class="revert-msg">
          Revert Reason: ${r.revert_message || "Reverted without reason string"}
        </div>
        <div class="result-detail" style="font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); margin-top: 4px;">
          Raw Revert Data: ${r.raw_return_data}
        </div>
      `;
    }
    resultsList.appendChild(item);
  });
}

// Event Listeners
document.getElementById("btn-scenario-account").addEventListener("click", () => selectScenario("account"));
document.getElementById("btn-scenario-partial").addEventListener("click", () => selectScenario("partial"));
document.getElementById("btn-scenario-token").addEventListener("click", () => selectScenario("token"));
btnExecute.addEventListener("click", executeBatch);

document.getElementById("btn-add-action").addEventListener("click", () => {
  const customAction = {
    target: MULTICALL3_ADDRESS,
    call_data: "0x42cbb15c",
    description: `Custom MultiCall3 Action #${currentManifest.actions.length + 1}`,
    action_type: "read",
    expected_result_type: "uint256"
  };
  currentManifest.actions.push(customAction);
  renderActions();
});

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  fetchStatus();
  renderActions();
  setInterval(fetchStatus, 15000); // Poll block height every 15s
});
