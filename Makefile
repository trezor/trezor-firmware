CC     = gcc
CFLAGS = -Wall -Wextra -Os
OBJS   = bignum.o ecdsa.o secp256k1.o sha2.o rand.o hmac.o bip32.o ripemd160.o bip39.o pbkdf2.o
OBJS  += aescrypt.o aeskey.o aestab.o

all: tests test-openssl

%.o: %.c %.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	gcc tests.o $(OBJS) -lcheck -o tests

test-openssl: test-openssl.o $(OBJS)
	gcc test-openssl.o $(OBJS) -o test-openssl -lcrypto

clean:
	rm -f *.o tests test-openssl
