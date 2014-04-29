all: messages.pb.c storage.pb.c types.pb.c

%.pb.c: %.pb %.options
	nanopb $< -L '#include "%s"' -T

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb *.o *.pb.c *.pb.h
