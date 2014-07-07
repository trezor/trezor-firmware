CC        = gcc

OPTFLAGS  = -Os -g

CFLAGS   += $(OPTFLAGS) \
            -W \
            -Wall \
            -Wextra \
            -Wimplicit-function-declaration \
            -Wredundant-decls \
            -Wstrict-prototypes \
            -Wundef \
            -Wshadow \
            -Wpointer-arith \
            -Wformat \
            -Wreturn-type \
            -Wsign-compare \
            -Wmultichar \
            -Wformat-nonliteral \
            -Winit-self \
            -Wuninitialized \
            -Wformat-security \
            -Werror

# disable sequence point warning because of AES code
CFLAGS += -Wno-sequence-point

# disable certain optimizations and features when small footprint is required
ifdef SMALL
CFLAGS += -DUSE_PRECOMPUTED_IV=0 -DUSE_PRECOMPUTED_CP=0 -DUSE_PUBKEY_VALIDATE=0
endif

OBJS   = bignum.o ecdsa.o secp256k1.o rand.o hmac.o bip32.o bip39.o pbkdf2.o base58.o
OBJS  += ripemd160.o
OBJS  += sha2.o
OBJS  += aescrypt.o aeskey.o aestab.o aes_modes.o

TESTLIBS = -lcheck -lrt -lpthread -lm
TESTSSLLIBS = -lcrypto

all: tests test-openssl

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	gcc tests.o $(OBJS) $(TESTLIBS) -o tests

test-openssl: test-openssl.o $(OBJS)
	gcc test-openssl.o $(OBJS) $(TESTSSLLIBS) -o test-openssl

clean:
	rm -f *.o tests test-openssl
