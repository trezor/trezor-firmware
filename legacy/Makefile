ifneq ($(EMULATOR),1)
OBJS += startup.o
endif

OBJS += buttons.o
OBJS += common.o
OBJS += flash.o
OBJS += layout.o
OBJS += oled.o
OBJS += rng.o
OBJS += dev_info.o

ifneq ($(EMULATOR),1)
OBJS += setup.o
OBJS += sys.o
OBJS += si2c.o
OBJS += mi2c.o
OBJS += usart.o
OBJS += nordic_dfu.o
OBJS += ble.o
OBJS += trans_fifo.o

OBJS += segger_rtt/SEGGER_RTT.o
OBJS += segger_rtt/SEGGER_RTT_printf.o
OBJS += segger_rtt/rtt_log.o
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
OBJS += gen/prompt.o

libtrezor.a: $(OBJS)

include Makefile.include

libtrezor.a:
	@printf "  AR      $@\n"
	$(Q)$(AR) rcs $@ $^

.PHONY: vendor

vendor:
	git submodule update --init --recursive
