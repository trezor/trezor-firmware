# Card model server and its native end-to-end test with the vault card backend.
ROOT := ../..
CRYPTO := $(ROOT)/crypto
CARD := $(ROOT)/core/embed/sec/vault/card

CRYPTO_SRCS = bignum.c ecdsa.c curves.c secp256k1.c nist256p1.c rand.c \
	hmac.c bip32.c bip39.c bip39_english.c pbkdf2.c base58.c address.c \
	ripemd160.c sha2.c sha3.c hasher.c blake256.c blake2b.c groestl.c \
	memzero.c hmac_drbg.c rfc6979.c consteq.c rand_insecure.c \
	ed25519-donna/curve25519-donna-32bit.c \
	ed25519-donna/curve25519-donna-helpers.c \
	ed25519-donna/modm-donna-32bit.c \
	ed25519-donna/ed25519-donna-basepoint-table.c \
	ed25519-donna/ed25519-donna-32bit-tables.c \
	ed25519-donna/ed25519-donna-impl-base.c \
	ed25519-donna/ed25519.c ed25519-donna/curve25519-donna-scalarmult-base.c \
	ed25519-donna/ed25519-sha3.c ed25519-donna/ed25519-keccak.c

CFLAGS ?= -O2 -g
override CFLAGS += -std=gnu11 -Wall -Wextra -I$(CRYPTO) -I$(CARD) -I. \
	-I$(ROOT)/core/embed/sec/vault/inc \
	-DUSE_CARDANO=0 -DUSE_NEM=0 -DUSE_MONERO=0 -DUSE_ETHEREUM=1 \
	-DUSE_BIP32_CACHE=0 -DUSE_BIP39_CACHE=0 -DUSE_KECCAK=1 \
	-DUSE_INSECURE_PRNG=1 -DRAND_PLATFORM_INDEPENDENT=1 -DVAULT_SEAL_MODE=3

BUILD := build
CRYPTO_OBJS = $(addprefix $(BUILD)/crypto/,$(CRYPTO_SRCS:.c=.o))
MODEL_OBJS = $(BUILD)/card_model.o $(BUILD)/fault.o $(CRYPTO_OBJS)

all: $(BUILD)/card_model_server $(BUILD)/test_vault_card $(BUILD)/test_card_tap

test: $(BUILD)/test_vault_card test_tap
	$(BUILD)/test_vault_card

# A slow user over TCP: the card comes CARD_TAP_MS after the firmware asks
# for it and leaves after CARD_HOLD_MS without a command.
CARD_TEST_PORT ?= 38995
CARD_TAP_MS ?= 600
CARD_HOLD_MS ?= 300
test_tap: $(BUILD)/test_card_tap $(BUILD)/card_model_server
	@$(BUILD)/card_model_server -p $(CARD_TEST_PORT) -t $(CARD_TAP_MS) \
		-k $(CARD_HOLD_MS) 2>/dev/null & server=$$!; sleep 0.2; \
	TREZOR_CARD_PORT=$(CARD_TEST_PORT) CARD_TAP_MS=$(CARD_TAP_MS) \
		CARD_HOLD_MS=$(CARD_HOLD_MS) $(BUILD)/test_card_tap; \
	status=$$?; kill $$server; exit $$status

$(BUILD)/card_model_server: $(BUILD)/server.o $(MODEL_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(BUILD)/test_vault_card: $(BUILD)/test_vault_card.o $(BUILD)/vault_stub.o \
		$(BUILD)/vault_card.o $(BUILD)/transport_model.o $(MODEL_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

# The tap test waits for the card for 1.5 s instead of 30 s.
TAP_FLAGS = -DCARD_WAIT_MS=1500
$(BUILD)/test_card_tap: $(BUILD)/test_card_tap.o $(BUILD)/vault_stub.o \
		$(BUILD)/vault_card_tap.o $(BUILD)/transport_tcp.o $(MODEL_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(BUILD)/test_card_tap.o: CFLAGS += $(TAP_FLAGS)
$(BUILD)/vault_card_tap.o: $(CARD)/vault_card.c $(wildcard $(CARD)/*.h)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(TAP_FLAGS) -DVAULT_TEST -Werror -c -o $@ $<

$(BUILD)/transport_tcp.o: $(CARD)/transport_tcp.c $(wildcard $(CARD)/*.h)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -Werror -c -o $@ $<

$(BUILD)/vault_card.o: $(CARD)/vault_card.c $(wildcard $(CARD)/*.h) \
		$(ROOT)/core/embed/sec/vault/inc/sec/vault_card.h
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -DVAULT_TEST -Werror -c -o $@ $<

$(BUILD)/test_%.o $(BUILD)/vault_stub.o: CFLAGS += -DVAULT_TEST

$(BUILD)/%.o: %.c $(wildcard *.h) $(wildcard $(CARD)/*.h)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -Werror -c -o $@ $<

$(BUILD)/crypto/%.o: $(CRYPTO)/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf $(BUILD)

.PHONY: all test test_tap clean
