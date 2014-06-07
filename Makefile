CC     = gcc
CFLAGS = -Wall -Wextra -Os -Wno-sequence-point
OBJS   = bignum.o ecdsa.o secp256k1.o rand.o hmac.o bip32.o bip39.o pbkdf2.o base58.o
OBJS  += ripemd160.o
OBJS  += sha2.o
OBJS  += aescrypt.o aeskey.o aestab.o aes_modes.o

all: tests test-openssl

%.o: %.c %.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	gcc tests.o $(OBJS) -lcheck -o tests

test-openssl: test-openssl.o $(OBJS)
	gcc test-openssl.o $(OBJS) -o test-openssl -lcrypto

clean:
	rm -f *.o tests test-openssl
