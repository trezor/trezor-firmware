NAME  = bootloader

OBJS += bootloader.o
OBJS += signatures.o
OBJS += usb.o

# Overrides from libtrezor.
# Objects ending with 'small.o' are built with -Os to make the bootloader smaller.
CFLAGS += -DFONT_SKIP_FIXED=1
OBJS += ../buttons.small.o
OBJS += ../common.small.o
OBJS += ../flash.small.o
OBJS += ../gen/bitmaps.small.o
OBJS += ../gen/fonts.small.o
OBJS += ../layout.small.o
OBJS += ../memory.small.o
OBJS += ../oled.small.o
OBJS += ../random_delays.small.o
OBJS += ../rng.small.o
OBJS += ../setup.small.o
OBJS += ../startup.o
OBJS += ../supervise.small.o
OBJS += ../timer.small.o
OBJS += ../usb21_standard.small.o
OBJS += ../usb_standard.small.o
OBJS += ../util.small.o
OBJS += ../webusb.small.o
OBJS += ../winusb.small.o

# Overrides from trezor-crypto
CFLAGS += -DUSE_PRECOMPUTED_CP=0
CFLAGS += -DUSE_PRECOMPUTED_IV=0
OBJS += ../vendor/trezor-crypto/bignum.small.o
OBJS += ../vendor/trezor-crypto/ecdsa.small.o
OBJS += ../vendor/trezor-crypto/hmac_drbg.small.o
OBJS += ../vendor/trezor-crypto/memzero.small.o
OBJS += ../vendor/trezor-crypto/secp256k1.small.o
OBJS += ../vendor/trezor-crypto/sha2.small.o

OPTFLAGS ?= -Os

include ../Makefile.include

# Remove libtrezor from linking since we specified the small versions
LDLIBS := $(filter-out -ltrezor,$(LDLIBS))

align: $(NAME).bin
	./firmware_align.py $(NAME).bin
