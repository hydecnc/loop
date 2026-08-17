from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ClaudeTools = Literal["Bash", "Read", "Edit", "Write", "Grep", "Glob"]


@dataclass
class Config:
    """Configuration of the fuzzing loop.

    Attributes:
        instances: path to directory containing the collection of fuzzer instance logs/crashes
        instance_prefix: prefix to be used to label each instances
        workdir: syz-manager's workdir; must match "workdir" in the cfg passed to syz-manager
        workdir_dumps: path to where retired workdirs are collected
        prompt: path to the markdown file containing the prompt
        fuzzer_timeout: time, in seconds, to wait before analyzing the instance
        fuzzer_shutdown_grace: time, in seconds, to wait for syz-manager to terminate
        claude_model: model string of claude to be used for analysis
        claude_allowed_tools: list of
    """

    instances: Path = Path("./instances")
    instance_prefix: str = "instance"
    workdir: Path = Path.home() / "nvidia_bug_finding" / "workdir"
    workdir_dumps: Path = Path.home() / "nvidia_bug_finding" / "workdir_dumps"
    syzkaller: Path = Path("./StepStone-fuzzer")
    open_gpu_kernel_modules: Path = Path("./open-gpu-kernel-modules")
    prompt: str = Path("./instruction.md").read_text("utf-8")
    fuzzer_timeout: int = 60 * 60
    fuzzer_shutdown_grace: int = 90
    claude_model: str = "claude-opus-5"
    claude_allowed_tools: tuple[ClaudeTools, ...] = (
        "Bash",
        "Read",
        "Edit",
        "Write",
        "Grep",
        "Glob",
    )


config = Config()
