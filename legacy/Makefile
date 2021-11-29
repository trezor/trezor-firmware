ifneq ($(EMULATOR),1)
OBJS += setup.o
OBJS += startup.o
OBJS += timer.o
endif

OBJS += buttons.o
OBJS += common.o
OBJS += flash.o
OBJS += gen/bitmaps.o
OBJS += gen/fonts.o
OBJS += layout.o
OBJS += memory.o
OBJS += oled.o
OBJS += random_delays.o
OBJS += rng.o
OBJS += supervise.o
OBJS += usb21_standard.o
OBJS += usb_standard.o
OBJS += util.o
OBJS += webusb.o
OBJS += winusb.o

libtrezor.a: $(OBJS)

include Makefile.include

libtrezor.a:
	@printf "  AR      $@\n"
	$(Q)$(AR) rcs $@ $^

.PHONY: vendor

vendor:
	git submodule update --init --recursive
