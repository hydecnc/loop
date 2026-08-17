import os
import subprocess

from .config import config
from .fs_utils import latest_instance


def dump_workdir() -> None:
    if not config.workdir.exists():
        return

    config.workdir_dumps.mkdir(parents=True, exist_ok=True)
    base = config.workdir_dumps / f"{config.instance_prefix}-{latest_instance()}"
    dump_loc = base
    collision = 0
    while dump_loc.exists():
        collision += 1
        dump_loc = base.with_name(f"{base.name}.{collision}")

    _ = config.workdir.rename(dump_loc)
    print(f"Dumped previous workdir to {dump_loc}")


def launch_fuzzer() -> bool:
    # remake all components
    _ = subprocess.run(
        ["./tools/syz-env", "make", "clean"],
        cwd=config.syzkaller,
        check=True,
    )
    _ = subprocess.run(
        ["./tools/syz-env", "make", "generate"],
        cwd=config.syzkaller,
        check=True,
    )
    _ = subprocess.run(
        ["./tools/syz-env", "make", "nvidia"],
        cwd=config.syzkaller,
        check=True,
    )

    # setup workdir & corpus
    dump_workdir()
    os.makedirs(config.workdir)
    _ = subprocess.run(
        [
            "./bin/syz-db",
            "pack",
            "./gpu_instrumentation/seed",
            config.workdir / "corpus.db",
        ],
        cwd=config.syzkaller,
        check=True,
    )

    # run the fuzzer, teeing its output to the log the analysis reads
    with open(config.workdir / "log", "wb") as log:
        # timeout and syz-manager is assumed to be given permission to run as sudo without password
        manager = subprocess.run(
            [
                "sudo",
                "-n",
                "timeout",
                "--signal=INT",
                f"--kill-after={config.fuzzer_shutdown_grace}",
                f"{config.fuzzer_timeout}",
                "./bin/syz-manager",
                "-debug",
                "-config=tutorial/default.cfg",
            ],
            cwd=config.syzkaller,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if manager.returncode == 124:
        return True
    elif manager.returncode == 137:
        print("syz-manager killed forcefully. Check if the VM is still up.")
        return False

    print(
        f"syz-manager exited early ({manager.returncode}). See {config.workdir / 'log'}"
    )
    return False
