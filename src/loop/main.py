import subprocess

from .agent.agent import Verification
from .agent.claude import ClaudeAnalysisAgent, ClaudeVerificationAgent
from .config import config
from .fs_utils import copy_instance, latest_instance
from .fuzzer import launch_fuzzer


def commit_changes() -> None:
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


def analyze_instance() -> bool:
    agent = ClaudeAnalysisAgent()
    verifier = ClaudeVerificationAgent()
    verification: Verification | None = None

    analysis = agent.analyze_instance(latest_instance())

    attempt = 1
    while attempt < config.max_verification_attempt:
        verification = verifier.verify_changes(analysis)

        if verification.verified:
            return True

        analysis = agent.fix_analysis(verification)

        print(f"Verification of changes failed: {verification.reason}")
        attempt += 1

    return False


def run_fuzz_loop():
    while True:
        print("====Lauching Fuzzer====")
        if not launch_fuzzer():
            print("Fuzzer round failed. Stopping.")
            return

        print("====Copying Instance====")
        _ = copy_instance()

        print("====Analyzing Instance====")
        if not analyze_instance():
            print("Analysis failed. Stopping.")
            return

        print("====Committing Changes====")
        commit_changes()


def main() -> None:
    print("==========Loop Fuzzing==========")
    run_fuzz_loop()
