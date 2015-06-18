EMFLAGS = \
	-Os --closure 1 \
	--memory-init-file 0 \
	--pre-js pre.js --post-js post.js \
	-s EXPORTED_FUNCTIONS='["_hdnode_public_ckd", "_ecdsa_get_address"]'

SRC = ../bignum.c ../ecdsa.c ../secp256k1.c ../hmac.c ../bip32.c \
	../base58.c ../ripemd160.c ../sha2.c ../rand.c

test-node: node_modules trezor-crypto.js test.js
	node test.js

test-browserify.js: node_modules trezor-crypto.js test.js
	browserify test.js -o $@ --noparse=`pwd`/trezor-crypto.js
	@echo "open test.html in your favourite browser"

trezor-crypto.js: $(SRC)
	emcc $(EMFLAGS) -o $@ $^

node_modules:
	npm install

clean:
	rm -f trezor-crypto.js test-browserify.js
