#include "memory_injector.h"
#include <dirent.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <unistd.h>
#include <string.h>

struct GspMsgQueueInfo {
	uint64_t status_queue_iova;
	uint64_t status_queue_offset;
	uint64_t status_queue_size;
};

static int readMemoryRegion(const uint64_t base, const uint64_t offset,
			    const uint64_t size, const uint64_t amount)
{
	const uint64_t addr = base + offset;

	int dev = open("/dev/memory-injector", O_RDWR);
	if (dev == -1) {
		perror("[GPU INSTUMENTATION] open");
		return -1;
	}

	int retval;

	struct memory_injector_config config = {
		.base = base,
		.size = size,
	};

	// TODO: dynamic read buffer size
	uint8_t buf[4] = { 0 };
	struct memory_injector_req read_req = {
		.buf = (uint64_t)buf,
		.amount = amount,
		.offset = offset,
	};

	fprintf(stderr, "[GPU INSTUMENTATION] Setting memory region\n");
	retval = ioctl(dev, SET_MEMORY_REGION, &config);
	if (retval == -1) {
		fprintf(stderr,
			"[GPU INSTUMENTATION] Memory Region Setting Failed.\n");
		close(dev);
		return -1;
	}

	fprintf(stderr,
		"[GPU INSTUMENTATION] Reading current value of variable at %lx\n",
		addr);
	retval = ioctl(dev, READ_MEMORY, &read_req);
	if (retval == -1) {
		perror("[GPU INSTUMENTATION] ioctl");
		close(dev);
		return -1;
	}
	printf("[GPU INSTRUMENTATION] Value at 0x%lx+0x%lx: %02x %02x %02x %02x\n",
	       base, offset, buf[0], buf[1], buf[2], buf[3]);

	close(dev);
	return 0;
}

int main(int argc, char *argv[])
{
	uint64_t base = 0;
	uint64_t offset = 0;
	uint64_t size = 0;
	// TODO: add safety checking
	for (int i = 1; i < argc; ++i) {
		if (strcmp(argv[i], "--help") == 0 ||
		    strcmp(argv[i], "-h") == 0) {
			// TODO: make help page
			return 0;
		}
		if (strcmp(argv[i], "--base") == 0 ||
		    strcmp(argv[i], "-b") == 0) {
			base = strtoull(argv[++i], NULL, 16);
			continue;
		}
		if (strcmp(argv[i], "--offset") == 0 ||
		    strcmp(argv[i], "-o") == 0) {
			offset = strtoull(argv[++i], NULL, 16);
			continue;
		}
		if (strcmp(argv[i], "--size") == 0 ||
		    strcmp(argv[i], "-s") == 0) {
			size = strtoull(argv[++i], NULL, 16);
			continue;
		}
	}

	return readMemoryRegion(base, offset, size, 4);
}
