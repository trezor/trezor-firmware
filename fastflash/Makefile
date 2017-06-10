APPVER = fastflash

NAME  = bootloader

OBJS += bootloader.o
OBJS += signatures.o
OBJS += usb.o

OBJS += ../vendor/trezor-crypto/sha2.o

include ../Makefile.include

CFLAGS += -I../bootloader
