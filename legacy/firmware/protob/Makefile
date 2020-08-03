ifneq ($(V),1)
Q := @
endif

SKIPPED_MESSAGES := Binance Cardano DebugMonero Eos Monero Ontology Ripple SdProtect Tezos WebAuthn \
	DebugLinkRecordScreen DebugLinkReseedRandom DebugLinkShowText DebugLinkEraseSdCard DebugLinkWatchLayout \
	GetOwnershipProof OwnershipProof GetOwnershipId OwnershipId AuthorizeCoinJoin DoPreauthorized \
	CancelAuthorization

ifeq ($(BITCOIN_ONLY), 1)
SKIPPED_MESSAGES += Ethereum Lisk NEM Stellar
endif

all: messages_map.h messages_map_limits.h messages-bitcoin.pb.h messages-common.pb.h messages-crypto.pb.h messages-debug.pb.h messages-ethereum.pb.h messages-management.pb.h messages-nem.pb.h messages.pb.h messages-stellar.pb.h messages-lisk.pb.h messages_nem_pb2.py

PYTHON ?= python

%.pb.h: %.pb %.options
	@printf "  NANOPB  $@\n"
	$(Q)nanopb_generator $< \
		-L '#include "%s"' \
		-T -D . \
		-s "mangle_names:M_FLATTEN"
	@grep " CALLBACK, " $@ && echo "CALLBACK field found" && rm $@ && exit 1  || :

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
