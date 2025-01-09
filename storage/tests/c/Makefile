CC = cc

CFLAGS = -Wall -Wshadow -Wextra -Wpedantic -Werror -Wno-missing-braces
CFLAGS += -fPIC
CFALGS += -fsanitize=address,undefined
CFLAGS += -DTREZOR_MODEL_T2T1
CFLAGS += -DTREZOR_EMULATOR
CFLAGS += -DUSE_INSECURE_PRNG
CFLAGS += -DCONFIDENTIAL=""

LIBS =
INC = -I ../../../crypto -I ../.. -I .
BASE = ../../../

SRC  = storage/tests/c/flash.c
SRC += storage/tests/c/common.c
SRC += storage/tests/c/random_delays.c
SRC += storage/tests/c/test_layout.c
SRC += storage/flash_area.c
SRC += storage/storage.c
SRC += storage/storage_utils.c
SRC += storage/norcow.c
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
OBJ_QW = $(SRC:%.c=build_qw/%.o)

OUT = libtrezor-storage.so
OUT_QW = libtrezor-storage-qw.so

$(OUT): $(OBJ)
	$(CC) $(CFLAGS) -DFLASH_BIT_ACCESS -DFLASH_BLOCK_WORDS=1 $(LIBS) $(OBJ) -shared -o $(OUT)

$(OUT_QW): $(OBJ_QW)
	$(CC) $(CFLAGS) -DFLASH_BLOCK_WORDS=4 $(LIBS) $(OBJ_QW) -shared -o $(OUT_QW)

build/crypto/chacha20poly1305/chacha_merged.o: $(BASE)crypto/chacha20poly1305/chacha_merged.c
	mkdir -p $(@D)

	$(CC) $(CFLAGS) $(INC) -c $< -o $@
build_qw/crypto/chacha20poly1305/chacha_merged.o: $(BASE)crypto/chacha20poly1305/chacha_merged.c
	mkdir -p $(@D)
	$(CC) $(CFLAGS) $(INC) -c $< -o $@

build/%.o: $(BASE)%.c $(BASE)%.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -DFLASH_BIT_ACCESS -DFLASH_BLOCK_WORDS=1 $(INC) -c $< -o $@

build_qw/%.o: $(BASE)%.c $(BASE)%.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -DFLASH_BLOCK_WORDS=4  $(INC) -c $< -o $@

clean:
	rm -f $(OUT) $(OUT_QW) $(OBJ) $(OBJ_QW)
