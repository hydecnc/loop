import os
import shutil
import subprocess

from .config import config


def launch_fuzzer():
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
    shutil.rmtree(config.workdir, ignore_errors=True)
    os.makedirs(config.workdir, exist_ok=True)
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
            manager.terminate()
            _ = manager.wait()

    return manager
