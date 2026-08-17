import os
import re
import shutil
from pathlib import Path

from .config import config


def latest_instance() -> int:
    """Get the latest instance number."""
    return max(
        (
            int(m.group(1))
            for p in config.instances.glob(f"{config.instance_prefix}-*")
            if (m := re.fullmatch(rf"{config.instance_prefix}-(\d+)", p.name))
        ),
        default=0,
    )


def copy_instance():
    """Copy relevant files from the currently running instance to be analyzed.

    TODO: crash selection
    """
    console_logs = config.workdir / "log"
    crashes = config.workdir / "crashes"

    instance_num = latest_instance()
    instance = config.instances / f"{config.instance_prefix}-{instance_num + 1}"
    instance.mkdir(parents=True, exist_ok=True)

    with os.scandir(crashes) as it:
        empty = not any(it)

    if empty:
        shutil.copy(console_logs, instance / "log")
    else:
        shutil.copytree(crashes, instance / "crashes", dirs_exist_ok=True)

    return instance


def choose_crash(crash_dir: Path) -> Path:
    """Choose the crash to be analyzed in the instance.

    TODO: Implement logic to choose crash
    """
    with os.scandir(crash_dir) as crashes:
        for crash in crashes:
            print(f"Crash id {crash.name} found.")

    return Path()
