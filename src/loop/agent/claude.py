import asyncio
from pathlib import Path
from typing import Any, cast, override

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)

from ..config import config
from .agent import Analysis, AnalysisAgent, Verification, VerificationAgent


class ClaudeAnalysisAgent(AnalysisAgent):
    def __init__(self) -> None:
        options: ClaudeAgentOptions = ClaudeAgentOptions(
            model=config.claude_model,
            cwd=Path.cwd(),
            allowed_tools=["Bash", "Read", "Edit", "Write", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=config.claude_max_turns,
            setting_sources=[],
            output_format={
                "type": "json_schema",
                "schema": Analysis.model_json_schema(),
            },
        )
        self._client: ClaudeSDKClient = ClaudeSDKClient(options)

    async def __aenter__(self) -> ClaudeAnalysisAgent:
        await self._client.connect()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        await self._client.disconnect()

    @override
    async def _analysis(self, prompt: str) -> Analysis:
        result: ResultMessage | None = None
        await self._client.query(prompt)
        async for message in self._client.receive_response():
            if isinstance(message, ResultMessage):
                result = message

        if result is None or result.is_error:
            raise RuntimeError(f"analysis agent did not finish: {result}")

        structured_output = cast(dict[str, Any] | None, result.structured_output)  # pyright: ignore[reportExplicitAny]
        if structured_output is None:
            raise RuntimeError(
                f"no structured output: (stop reason: {result.stop_reason}, terminal reason: {result.terminal_reason}"
            )

        return Analysis.model_validate(structured_output)

    @override
    async def analyze_instance(self, iteration: int) -> Analysis:
        instance = config.instances / f"{config.instance_prefix}-{iteration}"
        log = instance / "log"
        crashes = instance / "crashes"

        if not log.exists() and not crashes.is_dir():
            raise RuntimeError(f"Nothing to analyze under {instance}")

        print(
            f"Analyzing {instance.name} ({'crash' if crashes.is_dir() else 'quiet'})."
        )

        tail = f"\nRound: {iteration}"
        tail += f"\nCrashes: {crashes}" if crashes.is_dir() else f"\nLog: {log}"
        print(tail)

        result = await self._analysis(config.analysis_prompt + tail)

        return result

    @override
    async def fix_analysis(self, verification: Verification) -> Analysis:
        prompt = f"""Your previous analysis failed to be verified for the following reason:
{verification.reason}

Address this issue appropriately by fixing the files on disk.
Then, re-emit the corrected analysis of this round.
"""
        result = await self._analysis(prompt)

        return result


class ClaudeVerificationAgent(VerificationAgent):
    def __init__(self) -> None:
        self._options: ClaudeAgentOptions = ClaudeAgentOptions(
            model=config.claude_model,
            cwd=Path.cwd(),
            tools=["Read", "Grep", "Glob", "Bash"],
            allowed_tools=["Read", "Grep", "Glob", "Bash"],
            permission_mode="dontAsk",
            max_turns=config.claude_max_turns,
            setting_sources=[],
            output_format={
                "type": "json_schema",
                "schema": Verification.model_json_schema(),
            },
        )

    @override
    async def _run_agent(self, prompt: str) -> Verification:
        result: ResultMessage | None = None
        async for message in query(prompt=prompt, options=self._options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
            elif isinstance(message, ResultMessage):
                result = message

        if result is None or result.is_error:
            raise RuntimeError(f"verification agent did not finish: {result}")

        structured_output = cast(dict[str, Any] | None, result.structured_output)  # pyright: ignore[reportExplicitAny]
        if structured_output is None:
            raise RuntimeError(
                f"no structured output: (stop reason: {result.stop_reason}, terminal reason: {result.terminal_reason}"
            )
        return Verification.model_validate(structured_output)

    @override
    async def verify_changes(self, analysis: Analysis) -> Verification:
        print("Verifying changes")

        return await self._run_agent(
            f"{config.verification_prompt}\n## Agent's claim & changes\n{analysis}"
        )
