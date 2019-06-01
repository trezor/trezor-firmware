EMULATOR := 1

OBJS += setup.o

OBJS += memory.o
OBJS += oled.o
OBJS += rng.o
OBJS += timer.o

ifndef PIZERO
OBJS += buttons.o
OBJS += udp.o
endif

OBJS += strl.o

libemulator.a: $(OBJS)
	$(AR) rcs $@ $(OBJS)

include ../Makefile.include
