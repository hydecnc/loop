import re
import subprocess
from pathlib import Path

PROMPT = Path("./instruction.md").read_text("utf-8")
INSTANCES = Path("./instances")
REPOS = ("./StepStone-fuzzer/", "./ogkm/")

MODEL = "claude-opus-5"
ALLOWED_TOOLS = "Bash,Read,Edit,Write,Grep,Glob"


def latest_instance() -> int | None:
    rounds = [
        int(m.group(1))
        for p in INSTANCES.glob("instance-*")
        if (m := re.fullmatch(r"instance-(\d+)", p.name))
    ]
    return max(rounds) if rounds else None


def run_claude(prompt: str, project_dir: str = ".") -> int:
    result = subprocess.run(
        [
            "claude",
            "-p",
            "--model",
            MODEL,
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            ALLOWED_TOOLS,
        ],
        input=prompt,
        cwd=project_dir,
        text=True,
    )
    return result.returncode


def analyze_fuzz(iteration: int) -> bool:
    instance = INSTANCES / f"instance-{iteration}"
    log = instance / "log"
    report = instance / "report"

    if not log.exists():
        print(f"No log at {log}. Copy the run's log there first.")
        return False

    print(
        f"Analyzing instance-{iteration} ({'crash' if report.exists() else 'quiet'})."
    )

    tail = (
        f"\nRound: {iteration}"
        f"\nLog: {log}"
        f"\nReport: {report if report.exists() else 'Does not exist.'}"
    )
    print(tail)

    code = run_claude(PROMPT + tail)
    if code != 0:
        print(f"claude exited {code}.")
        return False

    print("Commit the changes (c), then run the fuzzer with them.")
    print(
        "Before the next analysis, copy that run's log/report to instances/instance-N."
    )
    return True


def commit_changes() -> None:
    print("Committing changes in fuzzer and ogkm...")

    for repo in REPOS:
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


def main() -> None:
    print("==Loop Fuzzing==")
    print("r: analyze latest instance | c: commit | q: quit")

    changes_committed = True

    while True:
        cmd = input("Type in the command here: ")
        match cmd:
            case "q":
                print("Quitting...")
                return
            case "r":
                if not changes_committed:
                    if input("WARN: changes not committed. Proceed? [y/N] ") != "y":
                        continue

                iteration = latest_instance()
                if iteration is None:
                    print(f"No instances under {INSTANCES}.")
                    continue

                if analyze_fuzz(iteration):
                    changes_committed = False
            case "c":
                commit_changes()
                changes_committed = True
            case _:
                pass
