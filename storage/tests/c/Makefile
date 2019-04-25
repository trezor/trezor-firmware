CC = gcc
CFLAGS = -Wall -Wshadow -Wextra -Wpedantic -Werror -fPIC -DTREZOR_STORAGE_TEST
LIBS =
INC = -I ../../../crypto -I ../../../storage -I .
OBJ = flash.o common.o
OBJ += ../../../storage/storage.o ../../../storage/norcow.o
OBJ += ../../../crypto/pbkdf2.o
OBJ += ../../../crypto/rand.o
OBJ += ../../../crypto/chacha20poly1305/rfc7539.o
OBJ += ../../../crypto/chacha20poly1305/chacha20poly1305.o
OBJ += ../../../crypto/chacha20poly1305/poly1305-donna.o
OBJ += ../../../crypto/chacha20poly1305/chacha_merged.o
OBJ += ../../../crypto/hmac.o
OBJ += ../../../crypto/sha2.o
OBJ += ../../../crypto/memzero.o
OUT = libtrezor-storage.so

$(OUT): $(OBJ)
	$(CC) $(CFLAGS) $(LIBS) $(OBJ) -shared -o $(OUT)

%.o: %.c %.h
	$(CC) $(CFLAGS) $(INC) -c $< -o $@

clean:
	rm -f $(OUT) $(OBJ)
