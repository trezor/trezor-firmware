NAME  = bootloader

OBJS += bootloader.o
OBJS += signatures.o
OBJS += usb.o

OBJS += ../trezor-crypto/bignum.o
OBJS += ../trezor-crypto/ecdsa.small.o
OBJS += ../trezor-crypto/hmac.o
OBJS += ../trezor-crypto/ripemd160.o
OBJS += ../trezor-crypto/secp256k1.small.o
OBJS += ../trezor-crypto/sha2.o

CFLAGS += -DUSE_PRECOMPUTED_IV=0
CFLAGS += -DUSE_PRECOMPUTED_CP=0

include ../Makefile.include

align:
	./firmware_align.py $(NAME).bin
