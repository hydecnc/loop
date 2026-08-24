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

Finally, modify `src/loop/config.py` accordingly.

## Recommendation

It is recommended to create new branches for StepStone-fuzzer and open-gpu-kernel-modules.
