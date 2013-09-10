CC     = gcc
CFLAGS = -Wall -Os
OBJS   = aux.o ecdsa.o secp256k1.o sha2.o rand.o

all: test-speed test-verify

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

test-speed: test-speed.o $(OBJS)
	gcc test-speed.o $(OBJS) -o test-speed

test-verify: test-verify.o $(OBJS)
	gcc test-verify.o $(OBJS) -o test-verify -lcrypto

clean:
	rm -f $(OBJS) test-speed test-verify
