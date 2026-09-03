# Loop

Fuzzing loop to discover bugs similar to GPUBreach.

To run the project with `uv`,

```bash
uv run loop
```

## Prerequisite

Clone the repository and initialize its submodules:

```bash
git clone https://github.com/hydecnc/loop.git
git submodule update --init --recursive
```

### StepStone-fuzzer setup

Fetch linux kernel source and unpack it.

```bash
mkdir -p /path/to/linux &&
cd /path/to/linux

curl -L -O https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.8.tar.xz
tar -xf linux-6.8.tar.xz
```

Then build the image used for StepStone-fuzzer:

```bash
cd StepStone-fuzzer
./tools/deploy-gpu-fuzz-image.sh \
  --linux /path/to/linux \
  --image /path/to/image-dir \
  --vendor nvidia
```

GPU Passthrough is required to run StepStone-fuzzer.
See detailed [setup instructions](https://github.com/bryansteiner/gpu-passthrough-tutorial).

The fuzzer, `syz-manager` must be ran as sudo, hence the temporary workaround is to allow the binary to run as sudo without password.
This can be done by putting the following line in any file under `/etc/sudoers.d/`:

```bash
username ALL=(root) NOPASSWD: /usr/bin/timeout --signal\=INT --kill-after\=* * ./bin/syz-manager -debug -config\=tutorial/default.cfg
```

Also, the generated image must have the [injection kernel module](./memory_injector/) installed.

Finally, modify `src/loop/config.py` accordingly.

## Recommendation

It is recommended to create new branches for StepStone-fuzzer and open-gpu-kernel-modules.
