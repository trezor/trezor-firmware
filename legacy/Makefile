ifneq ($(EMULATOR),1)
OBJS += startup.o
endif

OBJS += buttons.o
OBJS += common.o
OBJS += flash.o
OBJS += layout.o
OBJS += oled.o
OBJS += random_delays.o
OBJS += rng.o

ifneq ($(EMULATOR),1)
OBJS += setup.o
endif

OBJS += util.o
OBJS += memory.o
OBJS += supervise.o

ifneq ($(EMULATOR),1)
OBJS += timer.o
endif

OBJS += usb_standard.o
OBJS += usb21_standard.o
OBJS += webusb.o
OBJS += winusb.o

OBJS += gen/bitmaps.o
OBJS += gen/fonts.o

libtrezor.a: $(OBJS)

include Makefile.include

libtrezor.a:
	@printf "  AR      $@\n"
	$(Q)$(AR) rcs $@ $^

.PHONY: vendor

vendor:
	git submodule update --init --recursive
