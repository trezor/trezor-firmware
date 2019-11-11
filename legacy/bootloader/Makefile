NAME  = bootloader

OBJS += bootloader.o
OBJS += signatures.o
OBJS += usb.o

# overrides from libtrezor
CFLAGS += -DFONT_SKIP_FIXED=1
OBJS += ../gen/fonts.small.o

# overrides from trezor-crypto
CFLAGS += -DUSE_PRECOMPUTED_IV=0
CFLAGS += -DUSE_PRECOMPUTED_CP=0
OBJS += ../vendor/trezor-crypto/bignum.small.o
OBJS += ../vendor/trezor-crypto/ecdsa.small.o
OBJS += ../vendor/trezor-crypto/secp256k1.small.o
OBJS += ../vendor/trezor-crypto/sha2.small.o
OBJS += ../vendor/trezor-crypto/memzero.small.o
OBJS += ../vendor/trezor-crypto/hmac_drbg.small.o

OPTFLAGS ?= -Os

include ../Makefile.include

align: $(NAME).bin
	./firmware_align.py $(NAME).bin
