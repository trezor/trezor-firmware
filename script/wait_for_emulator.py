#!/usr/bin/env python3

import socket
import sys
import time

DEFAULT_ADDR = "127.0.0.1:21324"

if len(sys.argv) > 1:
    addr = sys.argv[1]
else:
    addr = DEFAULT_ADDR

host, port = addr.split(":")
SOCK_ADDR = (host, int(port))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(SOCK_ADDR)
sock.settimeout(0)

start = time.monotonic()
while True:
    try:
        sock.sendall(b"PINGPING")
        r = sock.recv(8)
        if r == b"PONGPONG":
            break
    except Exception:
        time.sleep(0.05)
end = time.monotonic()
print("waited for {:.3f}s".format(end - start))
