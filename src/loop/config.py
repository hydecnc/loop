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
        prompt:
        analysis_prompt: markdown file containing the prompt for analysis
        verification_prompt: markdown file containing the prompt for verification
        max_verification_attempt: maximum of verification attempts done for the analysis
        fuzzer_timeout: time, in seconds, to wait before analyzing the instance
        fuzzer_shutdown_grace: time, in seconds, to wait for syz-manager to terminate
        claude_model: model string of claude to be used for analysis
        claude_max_turns: max turns each claude agent performs
    """

    instances: Path = Path("./instances")
    instance_prefix: str = "instance"
    workdir: Path = Path.home() / "nvidia_bug_finding" / "workdir"
    workdir_dumps: Path = Path.home() / "nvidia_bug_finding" / "workdir_dumps"
    syzkaller: Path = Path("./StepStone-fuzzer")
    open_gpu_kernel_modules: Path = Path("./open-gpu-kernel-modules")
    analysis_prompt: str = Path("./prompt/analysis.md").read_text("utf-8")
    verification_prompt: str = Path("./prompt/verification.md").read_text("utf-8")
    max_verification_attempt: int = 10
    fuzzer_timeout: int = 60 * 60
    fuzzer_shutdown_grace: int = 90
    claude_model: str = "claude-opus-5"
    claude_max_turns: int = 60


config = Config()
