ifneq ($(V),1)
Q := @
endif

all: messages_map.h messages-bitcoin.pb.c messages-common.pb.c messages-crypto.pb.c messages-debug.pb.c messages-ethereum.pb.c messages-management.pb.c messages-nem.pb.c messages.pb.c messages-stellar.pb.c messages_nem_pb2.py

PYTHON ?= python

%.pb.c: %.pb %.options
	@printf "  NANOPB  $@\n"
	$(Q)$(PYTHON) ../../vendor/nanopb/generator/nanopb_generator.py $< -L '#include "%s"' -T

%.pb: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< -o $@

messages_%_pb2.py: messages-%.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< --python_out=.

%_pb2.py: %.proto
	@printf "  PROTOC  $@\n"
	$(Q)protoc -I/usr/include -I. $< --python_out=.

messages_map.h: messages_map.py messages_pb2.py
	$(Q)$(PYTHON) $< | grep -v -e MessageType_Cardano -e MessageType_Lisk -e MessageType_Tezos -e MessageType_Ripple -e MessageType_Stellar -e MessageType_Monero -e MessageType_DebugMonero > $@

clean:
	rm -f *.pb *.o *.d *.pb.c *.pb.h *_pb2.py messages_map.h
