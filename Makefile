CC = gcc
CFLAGS = -Wall
OBJS = aux.o ecdsa.o secp256k1.o sha256.o rand.o test.o
NAME = test

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

$(NAME): $(OBJS)
	gcc $(OBJS) -o $(NAME) -lcrypto

clean:
	rm -f $(OBJS) $(NAME)
