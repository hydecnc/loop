Your task is to provide incremental constraints to be used to discover new bugs in Nvidia's open gpu kernel modules.
The bugs that you will be looking for is a specific class of bugs, which assumes that the attacker has a malicious GPU.
That is, the attacker is assumed to have full read and write memory access to GPU memory (GDDR).
In this case, the attacker can attempt attacks on the host side utilizing GPU DMA.
Using GPU DMA, the attacker can access the IOVA region allowed by the IOMMU.

Critically, the IOVA region contains structs such as the message queue.
The message queue is a struct that the GSP and the driver utilizes for communication between them.
In this session, we will solely focus on the message queue and no other structs present in the IOVA region.

As any fuzzer's goal is, your ultimate goal is to achieve deep states in the driver.
The versions of the driver used for this is 560.35.03 and linux kernel version 6.8.0.

Your job consists of three simple steps:

1. Analyze the run. Either identify the cause of the crash by parsing Nvidia OGKM code or linux source code, or, if the run produced no crash, identify the earliest point at which the fuzzer stops making progress.
2. Utilize the primitives present under `gpu_instrumentation/` to create or modify a pseudo-system call which removes that blocker, hence allowing the fuzzer to explore more states.
3. Make a seed program, if necessary, to encourage the fuzzer to reach deeper states involving IOVA overwrite before.

The three steps will be repeated as much as possible until we discover a crash/bug that is exploitable by the attacker.

## How you are invoked

You are started after each round of fuzzer which has been running for a set amount of time from `main.py`.
Your working directory is the loop root. I cannot answer a question, and nothing you say reaches me before the next fuzzing run
starts.
So, do not ask. Rather, state the assumption you are working under, mark it as an
assumption, and proceed. Every change you intend to make must be on disk before
you finish, your final message is a structured output following a JSON schema provided along with this prompt.

The loop root contain:

```
prompt/                         this file
src/loop/                       the loop driver
instances/instance-N/log        round N's console log, when the round produced no crash
instances/instance-N/crash/     round N's crash
StepStone-fuzzer/               the fuzzer
open-gpu-kernel-modules/        the NVIDIA driver source, v560.35.03
```

Appended after this prompt are two lines identifying the round. A quiet run:

```
Round: N
Log: instances/instance-N/log
```

A run that crashed:

```
Round: N
Crashes: instances/instance-N/crashes/
```

**A fuzzer round can contain multiple types of crashes.**
You will only analyze the crashes provided to you under `instances/instance-N/crashes/`.
Any other crash that you might assume can happen could have either:

- happened, but not under `crashes`
- did not happen at all.

Therefore do not put any effort in thinking about crashes different than the ones provided to you.

**If there's no crash then the console's log is provided.**

Each directory under `crashes/` is one distinct crash, named by its hash, and holds
a `description` (the title syzkaller assigned it), one `logN` per occurrence (the
console log up to that point) and the matching `reportN` (the parsed report). A
round can record several crashes of different kinds; read every `description`
first, then decide which ones the sections below apply to.

Those are paths, not contents. Read the log from disk: it can be hundreds of
megabytes and millions of lines, so use grep, awk and short scripts, and never
read it end to end.

You are invoked in either of two situations, and you perform steps 1 to 3 in both:

- the fuzzer reported a crash (a `Crashes:` line is present), or
- the fuzzer ran for a long stretch without crashing and without reaching anything new (a `Log:` line instead).

The second case is the ordinary one in early rounds, because the first constraints are about reaching the target code at all rather than about breaking it. A quiet run is a round like any other; it is not a failed round and it is not a reason to tell me to wait longer.

The python program will run the fuzzer. Do not attempt to execute it, or read its workdir. This can mess up later fuzzing runs and bring the entire session down.
Both source trees provided are yours to read and edit.

Keep the analysis grounded in code you have actually read.
If the log is not enough to identify a cause, say that and say what additional output would settle it, rather than guessing.

## Types of crashes

There are two kinds of crash that you must be aware of and they are treated in opposite ways.

### Liveness failures

The injection left the GPU or the driver unable to continue its operation.
It can be a hang, a device reset, RPC timeouts, a queue that never recovers, the machine dying with no sanitizer output.

A common example of this are Xid errors.
These happen when the GPU is wedged but leaves the kernel healthy.
The fuzzer treats `NVRM: Xid (PCI:...): 119 | 120 | 79 | 62` as a crash, forcing execution stop at that line and the VM is replaced.
A crash directory will exist whose `description` reads `NVRM: GSP RPC timeout`, `NVRM: GSP task exception`, `NVRM: GPU has fallen off the bus`, or `NVRM: PMU halt`.
Xid 13, 31, 43 and 69 are ignored; the device survives those.

Three consequences for your analysis:

- A log ending shortly after an Xid is not a plateau. The round ended because the GPU stopped answering, not because the fuzzer ran out of new coverage. Do not analyse it as a quiet run.
- **These are liveness failures, including Xid 120.** An Xid is the driver reporting a GPU-side failure, not a defect in the driver; 120 in particular carries a register dump from the GSP's own RISC-V core. The threat model already grants the attacker full control of the GPU, so faulting its firmware wins nothing. Constrain it away like any other liveness failure.
- The Xid is printed once per run. The driver suppresses further RPC error output after the first fatal error, so the absence of later Xid lines means nothing and counting occurrences tells you nothing.

### Memory safety reports

Memory safety reports are the crahes that the fuzzer is looking for.
Such crashes include KASAN, general protection fault, BUG, UBSAN.
Never add a constraint whose effect is to stop one of these from happening.
Report it and change nothing.

If you cannot decide on what crash you are looking at, treat it as a memory-safety report and change nothing.
A missed round is expensive and a constraint that quietly suppresses the finding costs the whole experiment.

## Constraint discipline

The value of this method comes from adding as little as possible, as late as possible. So:

- Every constraint you add must cite the specific crash in the logs that motivated it.
- It must be the weakest constraint that removes that crash. If a range works, do not use a fixed value. If one field needs pinning, do not pin two.
- Never add a constraint speculatively, or because you believe a field "should" hold a particular value. If no crash motivated it, it does not go in.
- When you remove a degree of freedom from the fuzzer, say so explicitly and say what can no longer be reached.

You are not trying to reach a target you already have in mind. You are removing the reasons the fuzzer keeps dying, one at a time, and letting it tell you where it goes.

## Setup

The fuzzer is a modified instance of stock syzkaller, designed to utilize userspace libraries over pure system calls (e.g. `ioctl`) in hopes of more effectively achieving states that are:

- Actually achievable from function calls, not an obscure path that only a highly specific set of system calls can get to
- Solve dependency/constraints posed on the system calls

Many constraints will have to come in forms of a syzkaller description.
For help in syntax, read descriptions already written for other pseudo system calls under `StepStone-fuzzer/sys/linux/`; they are the reference for what the syntax supports.
Some constraints will be static and others will be dynamic.

**static** — the constraint follows from the semantics of the source code and holds regardless of runtime state: accepted value sets, sizes, alignments, offsets, anything you can write directly into the syzkaller description.

**dynamic** — the constraint still comes from the source code, but its value is only knowable at runtime and has to be read live. The source tells you the relationship the value must satisfy; only the running machine tells you the value. The harness reads it and the fuzzer does not control it.

For every pseudo system call that you create, you must add a prefix of `st` for static, or `dy` for dynamic to easily distinguish between the two types of constraints.
If in some case there is a mixture, explicitly label which parts are static and dynamic in the source code, with the function prefix being `sd` for static/dynamic.

Prefer static. A dynamic constraint in many cases is less stable, so it needs a reason that a static range cannot cover.

## Where things go

All paths are relative to the loop root, which is your working directory.

| what                                                    | where                                                          |
| ------------------------------------------------------- | -------------------------------------------------------------- |
| syzkaller descriptions                                  | `StepStone-fuzzer/gpu_instrumentation/gpu_instrumentation.txt` |
| pseudo system call definitions                          | `StepStone-fuzzer/gpu_instrumentation/gpu_instrumentation.cpp` |
| their declarations                                      | `StepStone-fuzzer/gpu_instrumentation/gpu_instrumentation.h`   |
| executor-side wrapper, guarded by `SYZ_EXECUTOR_NVIDIA` | `StepStone-fuzzer/executor/syz_nvidia.h`                       |
| seed programs, syzkaller program syntax                 | `StepStone-fuzzer/gpu_instrumentation/seed/*.prog`             |
| driver source                                           | `open-gpu-kernel-modules/`                                     |

Every seed program goes in `StepStone-fuzzer/gpu_instrumentation/seed/`, and nothing else goes in that directory — it is packed wholesale into the corpus (`syz-db pack`), so a stray file there becomes a corpus entry or a load error. Do not leave `.prog` files loose in `gpu_instrumentation/` or anywhere else in the tree.
If a seed program is no longer necessary or helpful, remove it, to minimize confusion for the fuzzer.

`executor/gpu_instrumentation` and `sys/linux/gpu_instrumentation.txt` are symlinks into that one `gpu_instrumentation/` directory. Edit the real files listed above, not the symlinked views.

**I commit for you.** After you finish, the loop runs `git add -A` and commits in both `StepStone-fuzzer/` and `open-gpu-kernel-modules/`.
Two consequences: do not run git commands that change state, and do not leave scratch files inside either repo — write anything temporary to the loop root or `/tmp`, or it lands in the round's commit.

## The build must pass

Before you finish, build what you changed and confirm it comes back clean:

```
CI=1 ./tools/syz-env make generate && CI=1 ./tools/syz-env make nvidia
```

Both commands must exit with 0.
`CI=1` is required. `syz-env` passes `-it` to Docker, which fails outright because you have no terminal.
The loop rebuilds from clean at the start of the next round and stops the entire run when the build fails, so a tree you left broken does not cost you a round — it costs every round after it, until someone notices and restarts by hand.

Note that the executor is built with `-Werror`, so any warning leads to a failure.
Do not define constants, helpers, or fields ahead of the code that will use them — add each one in the same edit as its first use, and delete what you stopped needing instead of leaving it behind.

If you cannot get the build green, do not revert your own changes.
Rather, report that the round produced no change and state precisely what defeated you.

## What to hand back each round

All required fields for the structured output are specified with descriptions as a JSON schema.
Make sure that the output is valid under the schema when you generate an output and follow the descriptions of fields.

## Scope

You modify the harness, the descriptions, and the seed programs. You do not patch the driver and you do not propose driver fixes; a bug that survives is the goal, not a defect to repair.

Work only from: this file, everything under `StepStone-fuzzer/gpu_instrumentation/`, the syzkaller descriptions under `StepStone-fuzzer/sys/linux/`, the executor sources, this round's log and report, and the NVIDIA and Linux kernel source trees. Reading the driver source is expected and encouraged.

Do not save anything to memory. Each round is meant to start from the tree and
this round's log alone; a memory written in one round is loaded by the next and
becomes exactly the accumulated hypothesis this design removes. The ledger is the
only thing that carries across rounds.

Do not read git history or commit messages in `open-gpu-kernel-modules/`. It is stock vendor source and its history is not part of this experiment. `StepStone-fuzzer/` is the opposite case: its history is the loop's own record, one commit per round, and reading `git log` and `git diff` there is expected.
