APPVER = 1.0.0

ifeq ($(FASTFLASH),1)
OBJS += fastflash.o
OBJS += bootloader.o
endif

NAME  = trezor

ifeq ($(EMULATOR),1)
OBJS += udp.o
else
OBJS += usb.o
endif

OBJS += bl_check.o
OBJS += u2f.o
OBJS += messages.o
OBJS += storage.o
OBJS += trezor.o
OBJS += pinmatrix.o
OBJS += fsm.o
OBJS += coins.o
OBJS += transaction.o
OBJS += protect.o
OBJS += layout2.o
OBJS += recovery.o
OBJS += reset.o
OBJS += signing.o
OBJS += crypto.o
OBJS += ethereum.o
OBJS += ethereum_tokens.o
OBJS += nem2.o
OBJS += nem_mosaics.o

OBJS += debug.o

OBJS += ../vendor/trezor-crypto/address.o
OBJS += ../vendor/trezor-crypto/bignum.o
OBJS += ../vendor/trezor-crypto/ecdsa.o
OBJS += ../vendor/trezor-crypto/curves.o
OBJS += ../vendor/trezor-crypto/secp256k1.o
OBJS += ../vendor/trezor-crypto/nist256p1.o
OBJS += ../vendor/trezor-crypto/rand.o
OBJS += ../vendor/trezor-crypto/memzero.o

OBJS += ../vendor/trezor-crypto/ed25519-donna/curve25519-donna-32bit.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/curve25519-donna-helpers.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/modm-donna-32bit.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519-donna-basepoint-table.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519-donna-32bit-tables.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519-donna-impl-base.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/curve25519-donna-scalarmult-base.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519-sha3.o
OBJS += ../vendor/trezor-crypto/ed25519-donna/ed25519-keccak.o

OBJS += ../vendor/trezor-crypto/hmac.o
OBJS += ../vendor/trezor-crypto/bip32.o
OBJS += ../vendor/trezor-crypto/bip39.o
OBJS += ../vendor/trezor-crypto/pbkdf2.o
OBJS += ../vendor/trezor-crypto/base32.o
OBJS += ../vendor/trezor-crypto/base58.o
OBJS += ../vendor/trezor-crypto/segwit_addr.o

OBJS += ../vendor/trezor-crypto/ripemd160.o
OBJS += ../vendor/trezor-crypto/sha2.o
OBJS += ../vendor/trezor-crypto/sha3.o
OBJS += ../vendor/trezor-crypto/blake256.o
OBJS += ../vendor/trezor-crypto/hasher.o

OBJS += ../vendor/trezor-crypto/aes/aescrypt.o
OBJS += ../vendor/trezor-crypto/aes/aeskey.o
OBJS += ../vendor/trezor-crypto/aes/aestab.o
OBJS += ../vendor/trezor-crypto/aes/aes_modes.o

OBJS += ../vendor/trezor-crypto/nem.o

OBJS += ../vendor/trezor-qrenc/qr_encode.o

OBJS += ../vendor/nanopb/pb_common.o
OBJS += ../vendor/nanopb/pb_decode.o
OBJS += ../vendor/nanopb/pb_encode.o

OBJS += protob/messages.pb.o
OBJS += protob/types.pb.o

include ../Makefile.include

ifeq ($(FASTFLASH),1)
CFLAGS += -DFASTFLASH=1
else
CFLAGS += -DFASTFLASH=0
endif

DEBUG_LINK ?= 0
DEBUG_LOG  ?= 0

CFLAGS += -Wno-sequence-point
CFLAGS += -I../vendor/nanopb -Iprotob -DPB_FIELD_16BIT=1
CFLAGS += -DQR_MAX_VERSION=0
CFLAGS += -DDEBUG_LINK=$(DEBUG_LINK)
CFLAGS += -DDEBUG_LOG=$(DEBUG_LOG)
CFLAGS += -DSCM_REVISION='"$(shell git rev-parse HEAD | sed 's:\(..\):\\x\1:g')"'
CFLAGS += -DUSE_ETHEREUM=1
CFLAGS += -DUSE_NEM=1

bootloader.o: ../fastflash/bootloader.bin
	$(OBJCOPY) -I binary -O elf32-littlearm -B arm \
		--redefine-sym _binary_$(shell echo -n "$<" | tr -c "[:alnum:]" "_")_start=__bootloader_start__ \
		--redefine-sym _binary_$(shell echo -n "$<" | tr -c "[:alnum:]" "_")_size=__bootloader_size__ \
		--rename-section .data=.rodata \
		$< $@

coins_count.h: coins-gen.py coins.json
	$(PYTHON) $< count > $@

coins_array.h: coins-gen.py coins.json
	$(PYTHON) $< array > $@

nem_mosaics.c nem_mosaics.h: nem_mosaics.py nem_mosaics.json
	$(PYTHON) $<

bl_data.h: bl_data-gen.py ../bootloader/bootloader.bin
	$(PYTHON) $<

clean::
	rm -f coins_count.h coins_array.h
	rm -f nem_mosaics.c nem_mosaics.h
	rm -f bl_data.h
