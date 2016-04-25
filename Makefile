CC        = gcc

OPTFLAGS  = -O3 -g

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
CFLAGS += -DED25519_CUSTOMRANDOM=1
CFLAGS += -DED25519_CUSTOMHASH=1
CFLAGS += -Ied25519-donna -I.

# disable certain optimizations and features when small footprint is required
ifdef SMALL
CFLAGS += -DUSE_PRECOMPUTED_IV=0 -DUSE_PRECOMPUTED_CP=0
endif

SRCS   = bignum.c ecdsa.c curves.c secp256k1.c nist256p1.c rand.c hmac.c bip32.c bip39.c pbkdf2.c base58.c
SRCS  += ripemd160.c
SRCS  += sha2.c
SRCS  += aescrypt.c aeskey.c aestab.c aes_modes.c
SRCS  += ed25519-donna/ed25519.c

OBJS   = $(SRCS:.c=.o)

TESTLIBS = -lcheck -lrt -lpthread -lm
TESTSSLLIBS = -lcrypto

all: tests test-openssl libtrezor-crypto.so

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	$(CC) tests.o $(OBJS) $(TESTLIBS) -o tests

test-openssl: test-openssl.o $(OBJS)
	$(CC) test-openssl.o $(OBJS) $(TESTSSLLIBS) -o test-openssl

libtrezor-crypto.so: $(SRCS)
	$(CC) $(CFLAGS) -fPIC -shared $(SRCS) -o libtrezor-crypto.so

clean:
	rm -f *.o ed25519-donna/*.o tests test-openssl libtrezor-crypto.so
