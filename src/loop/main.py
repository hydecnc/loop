import subprocess

from .analysis import analyze_instance
from .config import config
from .fs_utils import copy_instance
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


def run_fuzz_loop():
    while True:
        print("====Lauching Fuzzer====")
        _ = launch_fuzzer()
        print("====Copying Instance====")
        _ = copy_instance()
        print("====Committing Changes====")
        commit_changes()
        print("====Analyzing Instance====")
        if not analyze_instance():
            print("Analysis failed. Stopping.")
            return


def main() -> None:
    print("==========Loop Fuzzing==========")
    run_fuzz_loop()
