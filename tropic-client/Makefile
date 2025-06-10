TROPIC_PATH = ../vendor/libtropic
CRYPTO_PATH = ../crypto
TROPIC_SOURCE = $(wildcard $(TROPIC_PATH)/hal/crypto/trezor_crypto/*.c) $(wildcard *.c) $(TROPIC_PATH)/src/libtropic.c $(TROPIC_PATH)/src/lt_crc16.c $(TROPIC_PATH)/src/lt_hkdf.c $(TROPIC_PATH)/src/lt_l3.c $(TROPIC_PATH)/src/lt_random.c $(TROPIC_PATH)/src/lt_l1.c $(TROPIC_PATH)/src/lt_l1_port_wrap.c $(TROPIC_PATH)/src/lt_l3_process.c $(TROPIC_PATH)/src/lt_l2.c $(TROPIC_PATH)/src/lt_l2_frame_check.c $(TROPIC_PATH)/src/lt_asn1_der.c
CRYPTO_SOURCE = $(CRYPTO_PATH)/hmac.c $(CRYPTO_PATH)/sha2.c $(CRYPTO_PATH)/sha3.c $(CRYPTO_PATH)/hasher.c $(CRYPTO_PATH)/memzero.c $(wildcard $(CRYPTO_PATH)/aes/*.c) $(wildcard $(CRYPTO_PATH)/ed25519-donna/*.c) $(wildcard $(CRYPTO_PATH)/blake*.c) $(CRYPTO_PATH)/groestl.c $(CRYPTO_PATH)/ripemd160.c $(CRYPTO_PATH)/rand.c

main: $(TROPIC_SOURCE) $(CRYPTO_SOURCE)
	gcc -o main $(TROPIC_SOURCE) $(CRYPTO_SOURCE) -I$(TROPIC_PATH)/src -I$(TROPIC_PATH)/include -DLT_USE_TREZOR_CRYPTO=1 -I$(CRYPTO_PATH) -I$(CRYPTO_PATH)/aes -DAES_VAR -DUSE_INSECURE_PRNG
