APPVER = 1.8.0

NAME  = trezor

OBJS += trezor.o
OBJS += header.o
OBJS += bl_check.o
OBJS += ../vendor/trezor-crypto/memzero.o
OBJS += ../vendor/trezor-crypto/sha2.o

OPTFLAGS ?= -Os


../vendor/trezor-crypto/bip32.o: OPTFLAGS = -O3
../vendor/trezor-crypto/bip39.o: OPTFLAGS = -O3
../vendor/trezor-crypto/ecdsa.o: OPTFLAGS = -O3
../vendor/trezor-crypto/sha2.o: OPTFLAGS = -O3
../vendor/trezor-crypto/secp256k1.o: OPTFLAGS = -O3

include ../Makefile.include
CFLAGS:=$(filter-out -fstack-protector-all,$(CFLAGS))

DEBUG_LINK ?= 0
DEBUG_LOG  ?= 0

CFLAGS += -Wno-sequence-point
CFLAGS += -I../vendor/nanopb -Iprotob -DPB_FIELD_16BIT=1 -DPB_ENCODE_ARRAYS_UNPACKED=1 -DPB_VALIDATE_UTF8=1
CFLAGS += -DDEBUG_LINK=$(DEBUG_LINK)
CFLAGS += -DDEBUG_LOG=$(DEBUG_LOG)
CFLAGS += -DSCM_REVISION='"$(shell git rev-parse HEAD | sed 's:\(..\):\\x\1:g')"'
CFLAGS += -DUSE_MONERO=0
ifneq ($(BITCOIN_ONLY),1)
CFLAGS += -DUSE_ETHEREUM=1
CFLAGS += -DUSE_NEM=1
MAKO_RENDER_FLAG =
else
CFLAGS += -DUSE_ETHEREUM=0
CFLAGS += -DUSE_NEM=0
MAKO_RENDER_FLAG = --bitcoin-only
endif

%:: %.mako defs
	@printf "  MAKO    $@\n"
	$(Q)$(PYTHON) ../vendor/trezor-common/tools/cointool.py render $(MAKO_RENDER_FLAG) $@.mako

bl_data.h: bl_data.py bootloader.dat
	@printf "  PYTHON  bl_data.py\n"
	$(Q)$(PYTHON) bl_data.py

clean::
	rm -f bl_data.h
	find -maxdepth 1 -name "*.mako" | sed 's/.mako$$//' | xargs rm -f

FIRMWARE_T1_START   = 0x08010000
flash_intermediate_fw: trezor.bin
	openocd -f interface/stlink-v2.cfg -c "transport select hla_swd" -f target/stm32f2x.cfg -c "init; reset halt; flash write_image erase $< $(FIRMWARE_T1_START); exit"

openocd_reset:
	$(OPENOCD) -c "init; reset; exit"

