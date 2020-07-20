all: messages.pb.c

%.pb.c: %.pb %.options
	nanopb_generator $< -T -D . -s "mangle_names:M_FLATTEN"

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb *.o *.pb.c *.pb.h
