CC        = gcc

OPTFLAGS  = -O3 -g

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

# disable sequence point warning because of AES code
CFLAGS += -Wno-sequence-point
CFLAGS += -DED25519_CUSTOMRANDOM=1
CFLAGS += -DED25519_CUSTOMHASH=1
CFLAGS += -DED25519_NO_INLINE_ASM
CFLAGS += -DED25519_FORCE_32BIT=1
CFLAGS += -Ied25519-donna -Icurve25519-donna -I.
CFLAGS += -DUSE_ETHEREUM=1
CFLAGS += -DUSE_GRAPHENE=1

# disable certain optimizations and features when small footprint is required
ifdef SMALL
CFLAGS += -DUSE_PRECOMPUTED_IV=0 -DUSE_PRECOMPUTED_CP=0
endif

SRCS   = bignum.c ecdsa.c curves.c secp256k1.c nist256p1.c rand.c hmac.c bip32.c bip39.c pbkdf2.c base58.c
SRCS  += address.c
SRCS  += script.c
SRCS  += ripemd160.c
SRCS  += sha2.c
SRCS  += sha3.c
SRCS  += aescrypt.c aeskey.c aestab.c aes_modes.c
SRCS  += ed25519-donna/ed25519.c
SRCS  += curve25519-donna/curve25519.c
SRCS  += blake2s.c

OBJS   = $(SRCS:.c=.o)

TESTLIBS = -lcheck -lrt -lpthread -lm
TESTSSLLIBS = -lcrypto

all: tests test-openssl libtrezor-crypto.so test_speed tools

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	$(CC) tests.o $(OBJS) $(TESTLIBS) -o tests

test_speed: test_speed.o $(OBJS)
	$(CC) test_speed.o $(OBJS) -o test_speed

test-openssl: test-openssl.o $(OBJS)
	$(CC) test-openssl.o $(OBJS) $(TESTSSLLIBS) -o test-openssl

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
	rm -f *.o ed25519-donna/*.o curve25519-donna/*.o tests test_speed test-openssl libtrezor-crypto.so
	rm -f tools/*.o tools/xpubaddrgen tools/mktable tools/bip39bruteforce
