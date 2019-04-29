ifneq ($(V),1)
Q := @
endif

ifeq ($(BITCOIN_ONLY), 1)
SKIPPED_MESSAGES := Cardano Tezos Ripple Monero DebugMonero Ontology Tron Eos Binance Ethereum Lisk NEM Stellar
else
SKIPPED_MESSAGES := Cardano Tezos Ripple Monero DebugMonero Ontology Tron Eos Binance
endif

all: messages_map.h messages_map_limits.h messages-bitcoin.pb.c messages-common.pb.c messages-crypto.pb.c messages-debug.pb.c messages-ethereum.pb.c messages-management.pb.c messages-nem.pb.c messages.pb.c messages-stellar.pb.c messages-lisk.pb.c messages_nem_pb2.py

PYTHON ?= python

%.pb.c: %.pb %.options
	@printf "  NANOPB  $@\n"
	$(Q)$(PYTHON) ../../vendor/nanopb/generator/nanopb_generator.py $< \
		-L '#include "%s"' \
		-T \
		-s "mangle_names:M_FLATTEN"

%.pb: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< -o $@

messages_%_pb2.py: messages-%.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< --python_out=.

%_pb2.py: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< --python_out=.

messages_map.h messages_map_limits.h: messages_map.py messages_pb2.py
	$(Q)$(PYTHON) $< ${SKIPPED_MESSAGES}

clean:
	rm -f *.pb *.o *.d *.pb.c *.pb.h *_pb2.py messages_map.h messages_map_limits.h
