# RPC-IC220 firmware build.
#
# Produces target.bin: a raw image loaded at 0x08000000 by src/rig.py. Built
# inside the Docker build stage (deploy/Dockerfile); needs gcc-arm-none-eabi.
#
#   make            -> target.bin
#   make clean

CC      := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy
SIZE    := arm-none-eabi-size

# -O1 keeps the code compact without letting GCC hoist the volatile state array
# into registers. -fno-builtin stops it turning the byte copies into memcpy.
CFLAGS  := -mcpu=cortex-m0 -mthumb -O1 -fno-builtin -ffreestanding \
           -fno-common -Wall -Wextra -std=c11
LDFLAGS := -nostdlib -nostartfiles -T link.ld -Wl,--gc-sections

OBJS := target.o aes.o

all: target.bin

target.elf: $(OBJS) link.ld
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@
	$(SIZE) $@

target.bin: target.elf
	$(OBJCOPY) -O binary $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) target.elf target.bin

.PHONY: all clean
