all: messages.pb.c types.pb.c messages_map.h

PYTHON ?= python

%.pb.c: %.pb %.options
	$(PYTHON) ../../vendor/nanopb/generator/nanopb_generator.py $< -L '#include "%s"' -T

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

%_pb2.py: %.proto
	protoc -I/usr/include -I. $< --python_out=.

messages_map.h: messages_map.py messages_pb2.py types_pb2.py
	$(PYTHON) $< | grep -v -e MessageType_Lisk > $@

clean:
	rm -f *.pb *.o *.d *.pb.c *.pb.h *_pb2.py messages_map.h
