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

static inline void u32ToBuf(unsigned char buf[4], uint32_t num)
{
	buf[0] = (uint8_t)(num >> 0);
	buf[1] = (uint8_t)(num >> 8);
	buf[2] = (uint8_t)(num >> 16);
	buf[3] = (uint8_t)(num >> 24);
}

static int modifyMemoryRegion(const uint64_t base, const uint64_t offset,
			      const uint64_t size, const uint32_t value)
{
	const uint64_t addr = base + offset;
	uint8_t valueBuf[4];
	u32ToBuf(valueBuf, value);

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

	void *buf = malloc(sizeof(valueBuf));
	struct memory_injector_req read_req = {
		.buf = (uint64_t)buf,
		.amount = sizeof(valueBuf),
		.offset = offset,
	};
	struct memory_injector_req write_req = {
		.buf = (uint64_t)valueBuf,
		.amount = sizeof(valueBuf),
		.offset = offset,
	};

	fprintf(stderr, "[GPU INSTUMENTATION] Setting memory region\n");
	retval = ioctl(dev, SET_MEMORY_REGION, &config);
	if (retval == -1) {
		fprintf(stderr,
			"[GPU INSTUMENTATION] Memory Region Setting Failed.\n");
		free(buf);
		close(dev);
		return -1;
	}

	fprintf(stderr,
		"[GPU INSTUMENTATION] Reading current value of variable at %lx\n",
		addr);
	retval = ioctl(dev, READ_MEMORY, &read_req);
	if (retval == -1) {
		perror("[GPU INSTUMENTATION] ioctl");
		free(buf);
		close(dev);
		return -1;
	}
	if (fwrite(buf, 1, sizeof(valueBuf), stdout) != sizeof(valueBuf)) {
		perror("[GPU INSTUMENTATION] fwrite");
	}

	fprintf(stderr,
		"[GPU INSTUMENTATION] Writing value %u to variable at %lx\n",
		value, addr);
	retval = ioctl(dev, WRITE_MEMORY, &write_req);
	if (retval == -1) {
		perror("[GPU INSTUMENTATION] ioctl");
		free(buf);
		close(dev);
		return -1;
	}

	fprintf(stderr, "[GPU INSTUMENTATION] Reading new variable at %lx\n",
		addr);
	retval = ioctl(dev, READ_MEMORY, &read_req);
	if (retval == -1) {
		perror("[GPU INSTUMENTATION] ioctl");
		free(buf);
		close(dev);
		return -1;
	}
	if (fwrite(buf, 1, sizeof(valueBuf), stdout) != sizeof(valueBuf)) {
		perror("[GPU INSTUMENTATION] fwrite");
	}

	free(buf);
	close(dev);
	return 0;
}

static int instrument_gpu(const struct GspMsgQueueInfo *info,
			  const uint32_t value)
{
	int ret;
	if (!info)
		return -1;
	ret = modifyMemoryRegion(info->status_queue_iova,
				 info->status_queue_offset,
				 info->status_queue_size, value);

	return ret;
}

int main(int argc, char *argv[])
{
	uint64_t base = 0;
	uint64_t offset = 0;
	uint64_t size = 0;
	uint32_t value = 0;
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
		if (strcmp(argv[i], "--value") == 0) {
			value = strtoul(argv[++i], NULL, 10);
			continue;
		}
	}
	struct GspMsgQueueInfo info = {
		.status_queue_iova = base,
		.status_queue_offset = offset,
		.status_queue_size = size,
	};
	return instrument_gpu(&info, value);
}
