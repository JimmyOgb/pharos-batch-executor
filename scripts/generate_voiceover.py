import asyncio
import edge_tts

VOICEOVER_TEXT = (
    "Welcome to the Pharos Batch Executor demonstration for Task 10 on the Pharos Atlantic Testnet. "
    "We begin in the command line interface, querying live network status. "
    "The node confirms Atlantic Chain ID 688689 and the verified MultiCall3 contract deployment at 0xcA11. "
    "Next, we execute our partial failure batch manifest across three distinct contract queries. "
    "The batch succeeds, capturing actions one and three while cleanly isolating action two, "
    "which decodes the real OpenZeppelin revert reason: ERC20: transfer amount exceeds allowance. "
    "Now switching to the web dashboard, connected directly to the live Atlantic RPC. "
    "The status bar reflects the live block height and contract bytecode. "
    "We select the Account Inspection scenario with three configured actions and click Execute. "
    "All three actions succeed atomically, returning live block data, timestamp, and account balance. "
    "Next, we switch to the Partial Failure scenario and execute. "
    "Notice how actions one and three survive with green success badges, "
    "while action two displays a clear failure badge with the exact decoded revert string. "
    "We inspect the raw MultiCall3 calldata and the real hexadecimal node response. "
    "Finally, our honest gas analysis clearly distinguishes theoretical base transaction gas savings "
    "from execution gas, without making unverified net claims. "
    "This completes the Pharos Batch Executor live demonstration."
)

async def main():
    communicate = edge_tts.Communicate(VOICEOVER_TEXT, "en-US-ChristopherNeural", rate="+2%")
    await communicate.save("voiceover.mp3")
    print("Voiceover generated successfully as voiceover.mp3")

if __name__ == "__main__":
    asyncio.run(main())
