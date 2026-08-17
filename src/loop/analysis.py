import subprocess

from .config import config
from .fs_utils import latest_instance


def run_claude(prompt: str, project_dir: str = ".") -> int:
    result = subprocess.run(
        [
            "claude",
            "-p",
            "--model",
            config.claude_model,
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            ",".join(config.claude_allowed_tools),
        ],
        input=prompt,
        cwd=project_dir,
        text=True,
    )
    return result.returncode


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

    code = run_claude(config.prompt + tail)
    if code != 0:
        print(f"claude exited {code}.")
        return False

    return True
