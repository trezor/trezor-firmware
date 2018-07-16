check: messages.pb messages-bitcoin.pb messages-bootloader.pb messages-cardano.pb messages-common.pb messages-crypto.pb messages-debug.pb messages-ethereum.pb messages-lisk.pb messages-management.pb messages-nem.pb messages-ripple.pb messages-stellar.pb messages-tezos.pb

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb
