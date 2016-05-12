EMFLAGS = \
	-Os --closure 1 \
	--memory-init-file 0 \
	--pre-js pre.js --post-js post.js \
	-I ../ed25519-donna \
	-s EXPORTED_FUNCTIONS='["_hdnode_public_ckd_address_optimized", "_ecdsa_read_pubkey"]'

SRC = ../bignum.c ../ecdsa.c ../secp256k1.c ../hmac.c ../bip32.c \
	../base58.c ../ripemd160.c ../sha2.c ../rand.c

trezor-crypto.js: $(SRC)
	emcc $(EMFLAGS) -o $@ $^

test-node: node_modules trezor-crypto.js test.js
	node test.js

test-browserify.js: node_modules trezor-crypto.js test.js
	$(shell npm bin)/browserify test.js -o $@ --noparse=`pwd`/trezor-crypto.js
	@echo "open test.html in your favourite browser"

node_modules:
	npm install
	npm install browserify

clean:
	rm -f trezor-crypto.js test-browserify.js

docker:
	docker run --rm -i -v $(shell pwd)/..:/src -t apiaryio/emcc /bin/bash
