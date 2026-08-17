import os
import signal
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
        # syz-manager is assumed to be given permission to run as sudo without password
        manager = subprocess.Popen(
            [
                "sudo",
                "-n",
                "./bin/syz-manager",
                "-debug",
                "-config=tutorial/default.cfg",
            ],
            cwd=config.syzkaller,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            _ = manager.wait(timeout=config.fuzzer_timeout)
        except subprocess.TimeoutExpired:
            print("====Terminating Fuzzer====")
            manager.send_signal(signal.SIGINT)
            try:
                print(
                    f"Giving fuzzer {config.fuzzer_shutdown_grace}seconds before halting the loop process"
                )
                _ = manager.wait(timeout=config.fuzzer_shutdown_grace)
            except subprocess.TimeoutExpired:
                return False

    return True
