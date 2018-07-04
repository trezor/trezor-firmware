check: messages.pb

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb
