CC        = gcc

OPTFLAGS  = -O3

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
            -Werror \
            -I..

all: xpubaddrgen mktable bip39bruteforce

OBJS = ../bip32.o ../bip39.o ../ecdsa.o ../sha2.o ../bignum.o ../base58.o ../secp256k1.o ../nist256p1.o ../ripemd160.o ../hmac.o ../rand.o ../pbkdf2.o

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

xpubaddrgen: xpubaddrgen.o $(OBJS)
	$(CC) xpubaddrgen.o $(OBJS) -o xpubaddrgen

mktable: mktable.o $(OBJS)
	$(CC) mktable.o $(OBJS) -o mktable

bip39bruteforce: bip39bruteforce.o $(OBJS)
	$(CC) bip39bruteforce.o $(OBJS) -o bip39bruteforce

clean:
	rm -f *.o xpubaddrgen mktable bip39bruteforce
