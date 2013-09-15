CC     = gcc
CFLAGS = -Wall -Os
OBJS   = bignum.o ecdsa.o secp256k1.o sha2.o rand.o hmac.o bip32.o ripemd160.o

all: test-bip32 test-pubkey test-rfc6979 test-speed test-verify

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

test-bip32: test-bip32.o $(OBJS)
	gcc test-bip32.o $(OBJS) -o test-bip32

test-pubkey: test-pubkey.o $(OBJS)
	gcc test-pubkey.o $(OBJS) -o test-pubkey

test-rfc6979: test-rfc6979.o $(OBJS)
	gcc test-rfc6979.o $(OBJS) -o test-rfc6979

test-speed: test-speed.o $(OBJS)
	gcc test-speed.o $(OBJS) -o test-speed

test-verify: test-verify.o $(OBJS)
	gcc test-verify.o $(OBJS) -o test-verify -lcrypto

clean:
	rm -f *.o test-bip32 test-pubkey test-rfc6979 test-speed test-verify
