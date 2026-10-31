"""Network and contract configuration pinned for Pharos Atlantic Testnet."""

from dataclasses import dataclass

# Strict network pinning - Chain ID 688689
CHAIN_ID = 688689
CHAIN_ID_HEX = "0xa8231"
NETWORK_NAME = "Pharos Atlantic Testnet"
NATIVE_SYMBOL = "PHRS"

# Verified infrastructure endpoints
DEFAULT_RPC_URL = "https://atlantic.dplabs-internal.com"
HOSTED_MCP_URL = "https://mcp.pharos.xyz/mcp"
EXPLORER_URL = "https://atlantic.pharosscan.com"

# Verified on-chain contracts on Pharos Atlantic Testnet
MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"
USDC_ADDRESS = "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B"
WPHRS_ADDRESS = "0x838800b758277CC111B2d48Ab01e5E164f8E9471"

# Standard EVM constants
BASE_TX_INTRINSIC_GAS = 21000
MIN_BATCH_ACTIONS = 3

# MultiCall3 Function Selectors (keccak256 verified)
SELECTOR_TRY_AGGREGATE = "0xbce38bd7"   # tryAggregate(bool,(address,bytes)[])
SELECTOR_AGGREGATE3 = "0x82ad56cb"      # aggregate3((address,bool,bytes)[])
SELECTOR_AGGREGATE = "0x252dba42"       # aggregate((address,bytes)[])
SELECTOR_GET_BLOCK_NUMBER = "0x42cbb15c"  # getBlockNumber()
SELECTOR_GET_BLOCK_TIMESTAMP = "0x0f28c97d"  # getCurrentBlockTimestamp()
SELECTOR_GET_ETH_BALANCE = "0x4d2301cc"  # getEthBalance(address)
SELECTOR_GET_BASEFEE = "0x3e64a696"     # getBasefee()

# Standard EVM Revert Selectors
SELECTOR_REVERT_ERROR = "0x08c379a0"    # Error(string)
SELECTOR_REVERT_PANIC = "0x4e487b71"    # Panic(uint256)

PANIC_CODES = {
    0x00: "Generic compiler-inserted panic",
    0x01: "Assert condition evaluated to false",
    0x11: "Arithmetic operation underflowed or overflowed outside unchecked block",
    0x12: "Division or modulo by zero",
    0x21: "Converted invalid or out-of-range value to enum",
    0x22: "Accessed incorrectly encoded storage byte array",
    0x31: "Called .pop() on an empty array",
    0x32: "Array index out of bounds",
    0x41: "Allocated too much memory or array too large",
    0x51: "Called zero-initialized internal function pointer",
}
