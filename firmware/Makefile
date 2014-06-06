APPVER = 1.0.0

NAME  = trezor

OBJS += ssp.o
OBJS += usb.o
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

OBJS += debug.o

OBJS += ../trezor-crypto/bignum.o
OBJS += ../trezor-crypto/ecdsa.o
OBJS += ../trezor-crypto/secp256k1.o
OBJS += ../trezor-crypto/sha2.o
OBJS += ../trezor-crypto/hmac.o
OBJS += ../trezor-crypto/bip32.o
OBJS += ../trezor-crypto/ripemd160.o
OBJS += ../trezor-crypto/bip39.o
OBJS += ../trezor-crypto/pbkdf2.o
OBJS += ../trezor-crypto/aescrypt.o
OBJS += ../trezor-crypto/aeskey.o
OBJS += ../trezor-crypto/aestab.o

OBJS += protob/pb_decode.o
OBJS += protob/pb_encode.o
OBJS += protob/messages.pb.o
OBJS += protob/storage.pb.o
OBJS += protob/types.pb.o

include ../Makefile.include

# CFLAGS += -fstack-protector -fstack-protector-all
CFLAGS += -Iprotob -DPB_FIELD_16BIT=1
CFLAGS += -DDEBUG_LINK=0
CFLAGS += -DDEBUG_LOG=0
CFLAGS += -DSCM_REVISION='"$(shell git rev-parse HEAD | sed 's:\(..\):\\x\1:g')"'
