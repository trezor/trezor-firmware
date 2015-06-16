EMFLAGS = \
	-O2 --closure 1 \
	--memory-init-file 0 \
	--pre-js pre.js --post-js post.js \
	-s EXPORTED_FUNCTIONS='["_hdnode_public_ckd", "_ecdsa_get_address"]' \

SRC = ../bignum.c ../ecdsa.c ../secp256k1.c ../hmac.c ../bip32.c \
	../base58.c ../ripemd160.c ../sha2.c ../rand.c

test: trezor-crypto.js
	node test.js

trezor-crypto.js: $(SRC)
	emcc $(EMFLAGS) -o $@ $^

clean:
	rm -f trezor-crypto.js
