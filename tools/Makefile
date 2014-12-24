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

all: xpubaddrgen

OBJS = ../bip32.o ../ecdsa.o ../sha2.o ../bignum.o ../base58.o ../secp256k1.o ../ripemd160.o ../hmac.o ../rand.o

%.o: %.c %.h options.h
	$(CC) $(CFLAGS) -o $@ -c $<

xpubaddrgen: xpubaddrgen.o $(OBJS)
	$(CC) xpubaddrgen.o $(OBJS) -o xpubaddrgen

clean:
	rm -f *.o xpubaddrgen
