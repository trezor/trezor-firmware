ifneq ($(EMULATOR),1)
OBJS += startup.o
endif

OBJS += buttons.o
OBJS += layout.o
OBJS += oled.o
OBJS += rng.o
OBJS += serialno.o

ifneq ($(EMULATOR),1)
OBJS += setup.o
endif

OBJS += util.o
OBJS += memory.o

ifneq ($(EMULATOR),1)
OBJS += timer.o
endif

OBJS += gen/bitmaps.o
OBJS += gen/fonts.o

libtrezor.a: $(OBJS)
	$(AR) rcs libtrezor.a $(OBJS)

include Makefile.include

.PHONY: vendor

vendor:
	git submodule update --init
