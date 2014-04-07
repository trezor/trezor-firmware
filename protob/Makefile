check: config.pb messages.pb storage.pb types.pb

%.pb: %.proto
	protoc -I/usr/include -I. $< -o $@

clean:
	rm -f *.pb
