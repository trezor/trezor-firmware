OBJS += buttons.o
OBJS += layout.o
OBJS += oled.o
OBJS += rng.o
OBJS += serialno.o
OBJS += setup.o
OBJS += util.o
OBJS += memory.o
OBJS += timer.o
OBJS += gen/bitmaps.o
OBJS += gen/fonts.o

libtrezor.a: $(OBJS)
	$(AR) rcs libtrezor.a $(OBJS)

include Makefile.include

.PHONY: vendor

vendor:
	git submodule update --init
