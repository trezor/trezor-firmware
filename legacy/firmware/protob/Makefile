ifneq ($(V),1)
Q := @
endif

SKIPPED_MESSAGES := Binance Cardano DebugMonero Eos Monero Ontology Ripple SdProtect Tezos WebAuthn \
	DebugLinkRecordScreen DebugLinkEraseSdCard DebugLinkWatchLayout \
	DebugLinkLayout DebugLinkResetDebugEvents GetNonce \
	TxAckInput TxAckOutput TxAckPrev TxAckPaymentRequest \
	EthereumSignTypedData EthereumTypedDataStructRequest EthereumTypedDataStructAck \
	EthereumTypedDataValueRequest EthereumTypedDataValueAck ShowDeviceTutorial \
	UnlockBootloader AuthenticateDevice AuthenticityProof \
	Solana StellarClaimClaimableBalanceOp \
	ChangeLanguage TranslationDataRequest TranslationDataAck \
	SetBrightness DebugLinkOptigaSetSecMax ResetDeviceContinue GResetDeviceFinish \
	BenchmarkListNames BenchmarkRun BenchmarkNames BenchmarkResult

ifeq ($(BITCOIN_ONLY), 1)
SKIPPED_MESSAGES += Ethereum NEM Stellar
endif

PROTO_NAMES = messages messages-bitcoin messages-common messages-crypto messages-debug \
	messages-ethereum messages-ethereum-definitions messages-management messages-nem \
	messages-stellar options

PROTO_OPTIONS = $(PROTO_NAMES:=.options)
PROTO_COMPILED = $(PROTO_NAMES:=.pb)
PROTO_HEADERS = $(PROTO_COMPILED:=.h)

all: messages_map.h messages_map_limits.h messages.pb.h

PYTHON ?= python

# produces also all of $(PROTO_HEADERS)
messages.pb.h: $(PROTO_COMPILED) $(PROTO_OPTIONS)
	@printf "  NANOPB  $@\n"
	$(Q)nanopb_generator $(PROTO_COMPILED) \
		-L '#include "%s"' \
		-T -D . \
		-s "mangle_names:M_FLATTEN"
	@grep " CALLBACK, " $@ && echo "CALLBACK field found" && rm $@ && exit 1  || :

%.pb: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< -o $@

%_pb2.py: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< --python_out=.

messages_map.h messages_map_limits.h: messages_map.py messages_pb2.py options_pb2.py
	$(Q)$(PYTHON) $< ${SKIPPED_MESSAGES}

clean:
	rm -f *.pb *.o *.d *.pb.c *.pb.h *_pb2.py messages_map.h messages_map_limits.h
