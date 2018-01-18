CC       ?= gcc

OPTFLAGS ?= -O3 -g

CFLAGS   += $(OPTFLAGS) \
            -std=gnu99 \
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

CFLAGS += -I.
CFLAGS += -DUSE_ETHEREUM=1
CFLAGS += -DUSE_GRAPHENE=1
CFLAGS += -DUSE_NEM=1

# disable certain optimizations and features when small footprint is required
ifdef SMALL
CFLAGS += -DUSE_PRECOMPUTED_CP=0
endif

SRCS   = bignum.c ecdsa.c curves.c secp256k1.c nist256p1.c rand.c hmac.c bip32.c bip39.c pbkdf2.c base58.c base32.c
SRCS  += address.c
SRCS  += script.c
SRCS  += ripemd160.c
SRCS  += sha2.c
SRCS  += sha3.c
SRCS  += hasher.c
SRCS  += aes/aescrypt.c aes/aeskey.c aes/aestab.c aes/aes_modes.c
SRCS  += ed25519-donna/curve25519-donna-32bit.c ed25519-donna/curve25519-donna-helpers.c ed25519-donna/modm-donna-32bit.c
SRCS  += ed25519-donna/ed25519-donna-basepoint-table.c ed25519-donna/ed25519-donna-32bit-tables.c ed25519-donna/ed25519-donna-impl-base.c
SRCS  += ed25519-donna/ed25519.c ed25519-donna/curve25519-donna-scalarmult-base.c ed25519-donna/ed25519-sha3.c ed25519-donna/ed25519-keccak.c
SRCS  += blake256.c
SRCS  += blake2b.c blake2s.c
SRCS  += chacha20poly1305/chacha20poly1305.c chacha20poly1305/chacha_merged.c chacha20poly1305/poly1305-donna.c chacha20poly1305/rfc7539.c
SRCS  += rc4.c
SRCS  += nem.c
SRCS  += segwit_addr.c
SRCS  += memzero.c

OBJS   = $(SRCS:.c=.o)

TESTLIBS = $(shell pkg-config --libs check) -lpthread -lm
TESTSSLLIBS = -lcrypto

all: test_check test_openssl test_speed aes/aestst tools libtrezor-crypto.so

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

aes/aestst: aes/aestst.o aes/aescrypt.o aes/aeskey.o aes/aestab.o
	$(CC) $^ -o $@

test_check: test_check.o $(OBJS)
	$(CC) test_check.o $(OBJS) $(TESTLIBS) -o test_check

test_speed: test_speed.o $(OBJS)
	$(CC) test_speed.o $(OBJS) -o test_speed

test_openssl: test_openssl.o $(OBJS)
	$(CC) test_openssl.o $(OBJS) $(TESTSSLLIBS) -o test_openssl

libtrezor-crypto.so: $(SRCS)
	$(CC) $(CFLAGS) -fPIC -shared $(SRCS) -o libtrezor-crypto.so

tools: tools/xpubaddrgen tools/mktable tools/bip39bruteforce

tools/xpubaddrgen: tools/xpubaddrgen.o $(OBJS)
	$(CC) tools/xpubaddrgen.o $(OBJS) -o tools/xpubaddrgen

tools/mktable: tools/mktable.o $(OBJS)
	$(CC) tools/mktable.o $(OBJS) -o tools/mktable

tools/bip39bruteforce: tools/bip39bruteforce.o $(OBJS)
	$(CC) tools/bip39bruteforce.o $(OBJS) -o tools/bip39bruteforce

clean:
	rm -f *.o aes/*.o chacha20poly1305/*.o ed25519-donna/*.o
	rm -f test_check test_speed test_openssl libtrezor-crypto.so
	rm -f tools/*.o tools/xpubaddrgen tools/mktable tools/bip39bruteforce
