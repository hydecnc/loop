import asyncio
import subprocess

from .agent.agent import Analysis
from .agent.claude import ClaudeAnalysisAgent, ClaudeVerificationAgent
from .config import config
from .fs_utils import copy_instance, latest_instance
from .fuzzer import build_fuzzer, launch_fuzzer


def commit_changes() -> None:
    """Commit changes made to the fuzzer and GPU driver source.

    TODO: consider making GPU driver source immutable
    """
    print("Committing changes in fuzzer and ogkm...")

    for repo in (config.syzkaller, config.open_gpu_kernel_modules):
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )

        if not status.stdout.strip():
            print(f"No changes made to {repo}. Skipping commit.")
            continue

        _ = subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        _ = subprocess.run(
            ["git", "commit", "-m", "feat: apply claude changes"], cwd=repo, check=True
        )


def dump_analysis(analysis: Analysis) -> None:
    instance = config.instances / f"{config.instance_prefix}-{latest_instance()}"
    _ = (instance / "analysis.json").write_text(
        analysis.model_dump_json(indent=2), "utf-8"
    )


async def analyze_instance() -> bool:
    verifier = ClaudeVerificationAgent()

    async with ClaudeAnalysisAgent() as agent:
        analysis = await agent.analyze_instance(latest_instance())

        if analysis.memory_bug:
            print(f"Memory bug found! See {analysis}")
            dump_analysis(analysis)
            return True

        attempt = 1
        while attempt <= config.max_verification_attempt:
            verification = await verifier.verify_changes(analysis)

            if verification.verified:
                dump_analysis(analysis)
                return True

            analysis = await agent.fix_analysis(verification)

            print(f"Verification of changes failed: {verification.reason}")
            attempt += 1

        return False


def run_fuzz_loop():
    if not build_fuzzer(clean=True):
        print("Initial fuzzer build failed.")
        return

    while True:
        print("====Lauching Fuzzer====")
        if not launch_fuzzer():
            print("Fuzzer round failed. Stopping.")
            return

        print("====Copying Instance====")
        _ = copy_instance()

        print("====Analyzing Instance====")
        if not asyncio.run(analyze_instance()):
            print("Analysis failed. Stopping.")
            return

        print("====Committing Changes====")
        commit_changes()


def main() -> None:
    print("==========Loop Fuzzing==========")
    run_fuzz_loop()
