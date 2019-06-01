OBJS += pizero.o
OBJS += oled_drivers.o
OBJS += usb-gadget.o
OBJS += usb.o

libpizero.a: $(OBJS)
	$(AR) rcs $@ $(OBJS)

include ../../Makefile.include
