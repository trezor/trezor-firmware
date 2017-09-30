all: messages.pb.c storage.pb.c types.pb.c messages_map.h

%.pb.c: %.pb %.options
	../../vendor/nanopb/generator/nanopb_generator.py $< -L '#include "%s"' -T

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

%_pb2.py: %.proto
	protoc -I/usr/include -I. $< --python_out=.

messages_map.h: messages_map.py messages_pb2.py types_pb2.py
	./$< > $@

clean:
	rm -f *.pb *.o *.d *.pb.c *.pb.h *_pb2.py messages_map.h
