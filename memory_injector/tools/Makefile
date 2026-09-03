CC := gcc
CFLAGS := -Wall -O2 -I../

.PHONY: all clean

all: instrument_gpu read_memory

instrument_gpu: instrument_gpu.c
	$(CC) $(CFLAGS) -o $@ $<

read_memory: read_memory.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f instrument_gpu read_memory
