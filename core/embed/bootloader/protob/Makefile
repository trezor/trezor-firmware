all: messages.pb.c types.pb.c

%.pb.c: %.pb %.options
	nanopb_generator $< -T

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb *.o *.pb.c *.pb.h
