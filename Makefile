CC     = gcc
CFLAGS = -Wall -Os
OBJS   = bignum.o ecdsa.o secp256k1.o sha2.o rand.o hmac.o bip32.o ripemd160.o

all: tests test-speed test-verify

%.o: %.c %.h
	$(CC) $(CFLAGS) -o $@ -c $<

tests: tests.o $(OBJS)
	gcc tests.o $(OBJS) -lcheck -o tests

test-speed: test-speed.o $(OBJS)
	gcc test-speed.o $(OBJS) -o test-speed

test-verify: test-verify.o $(OBJS)
	gcc test-verify.o $(OBJS) -o test-verify -lcrypto

clean:
	rm -f *.o tests test-speed test-verify
