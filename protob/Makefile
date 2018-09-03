check: messages.pb messages-bitcoin.pb messages-bootloader.pb messages-cardano.pb messages-common.pb messages-crypto.pb messages-debug.pb messages-ethereum.pb messages-lisk.pb messages-management.pb messages-monero.pb messages-nem.pb messages-ripple.pb messages-stellar.pb messages-tezos.pb messages-ontology.pb messages-tron.pb

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

combine:
	echo 'syntax = "proto2";' > combined.proto
	echo 'import "google/protobuf/descriptor.proto";' >> combined.proto
	grep -hv -e '^import ' -e '^syntax' -e '^package' -e 'option java_' messages*.proto | sed 's/hw\.trezor\.messages\.common\.//' >> combined.proto

clean:
	rm -f *.pb
