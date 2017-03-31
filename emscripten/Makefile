EMFLAGS = \
	-Os --closure 1 \
	--memory-init-file 0 \
	--pre-js pre.js --post-js post.js \
	-I ../ed25519-donna \
	-s EXPORTED_FUNCTIONS='["_hdnode_public_ckd_address_optimized", "_ecdsa_read_pubkey"]'

SRC = ../bignum.c ../ecdsa.c ../secp256k1.c ../hmac.c ../bip32.c \
	../base58.c ../ripemd160.c ../sha2.c ../rand.c ../address.c

all: trezor-crypto.js benchmark-browserify.js

trezor-crypto.js: $(SRC)
	emcc $(EMFLAGS) -o $@ $^

benchmark-browserify.js: node_modules trezor-crypto.js benchmark.js
	$(shell npm bin)/browserify benchmark.js -o $@ --noparse=`pwd`/trezor-crypto.js
	@echo "open benchmark.html in your favourite browser"

benchmark-node: node_modules trezor-crypto.js benchmark.js
	node benchmark.js

node_modules:
	npm install
	npm install browserify

clean:
	rm -f trezor-crypto.js benchmark-browserify.js

docker:
	docker run --rm -i -v $(shell pwd)/..:/src -t apiaryio/emcc /bin/bash

docker-build:
	docker run --rm -v $(shell pwd)/..:/src apiaryio/emcc /bin/bash -c 'cd emscripten && make'

test-correctness: node_modules
	node test-correctness.js test-correctness-segwit-p2sh.js
