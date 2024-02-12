CC = cc

CFLAGS = -Wall -Wshadow -Wextra -Wpedantic -Werror -Wno-missing-braces
CFLAGS += -fPIC
CFALGS += -fsanitize=address,undefined
CFLAGS += -DTREZOR_MODEL_T
CFLAGS += -DUSE_INSECURE_PRNG

LIBS =
INC = -I ../../../crypto -I ../.. -I .
BASE = ../../../

SRC  = storage/tests/c3/flash.c
SRC += storage/tests/c3/common.c
SRC += storage/tests/c3/random_delays.c
SRC += storage/tests/c3/test_layout.c
SRC += storage/tests/c3/flash_common.c
SRC += storage/tests/c3/storage.c
SRC += storage/tests/c3/norcow.c
SRC += crypto/pbkdf2.c
SRC += crypto/rand.c
SRC += crypto/chacha20poly1305/rfc7539.c
SRC += crypto/chacha20poly1305/chacha20poly1305.c
SRC += crypto/chacha20poly1305/poly1305-donna.c
SRC += crypto/chacha20poly1305/chacha_merged.c
SRC += crypto/hmac.c
SRC += crypto/sha2.c
SRC += crypto/memzero.c

OBJ = $(SRC:%.c=build/%.o)

OUT = libtrezor-storage3.so

$(OUT): $(OBJ)
	$(CC) $(CFLAGS) $(LIBS) $(OBJ) -shared -o $(OUT)

build/crypto/chacha20poly1305/chacha_merged.o: $(BASE)crypto/chacha20poly1305/chacha_merged.c
	mkdir -p $(@D)
	$(CC) $(CFLAGS) $(INC) -c $< -o $@

build/%.o: $(BASE)%.c $(BASE)%.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) $(INC) -c $< -o $@

clean:
	rm -f $(OUT) $(OBJ)
