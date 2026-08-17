import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from .config import config
from .fs_utils import latest_instance


async def _execute_agent(prompt: str, transcript: Path) -> bool:
    options = ClaudeAgentOptions(
        model=config.claude_model,
        cwd=Path.cwd(),
        allowed_tools=list(config.claude_allowed_tools),
        permission_mode="acceptEdits",
        max_turns=60,
        setting_sources=[],
    )

    result: ResultMessage | None = None
    with transcript.open("w", encoding="utf-8") as file:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                        _ = file.write(block.text)
                    elif isinstance(block, ToolUseBlock):
                        _ = file.write(f"\n[{block.name}] {block.input}\n")
            elif isinstance(message, ResultMessage):
                result = message

    if result is None:
        print("No result. Agent did not finish.")
        return False

    print(result)
    return not result.is_error


def analyze_instance() -> bool:
    iteration = latest_instance()
    instance = config.instances / f"{config.instance_prefix}-{iteration}"
    log = instance / "log"
    crashes = instance / "crashes"

    if not log.exists() and not crashes.is_dir():
        print(f"Nothing to analyze under {instance}.")
        return False

    print(f"Analyzing {instance.name} ({'crash' if crashes.is_dir() else 'quiet'}).")

    tail = f"\nRound: {iteration}"
    tail += f"\nCrashes: {crashes}" if crashes.is_dir() else f"\nLog: {log}"
    print(tail)

    return asyncio.run(_execute_agent(config.prompt + tail, instance / "agent.txt"))
