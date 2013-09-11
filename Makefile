CC     = gcc
CFLAGS = -Wall -Os
OBJS   = aux.o ecdsa.o secp256k1.o sha2.o rand.o hmac.o

all: test-rfc6979 test-speed test-verify

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

test-rfc6979: test-rfc6979.o $(OBJS)
	gcc test-rfc6979.o $(OBJS) -o test-rfc6979

test-speed: test-speed.o $(OBJS)
	gcc test-speed.o $(OBJS) -o test-speed

test-verify: test-verify.o $(OBJS)
	gcc test-verify.o $(OBJS) -o test-verify -lcrypto

clean:
	rm -f $(OBJS) test-speed test-verify
