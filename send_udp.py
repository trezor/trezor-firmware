#!/usr/bin/python
import socket
import os

UDP_IP = os.getenv('TREZOR_UDP_IP', '127.0.0.1')
UDP_PORT = int(os.getenv('TREZOR_UDP_PORT', '21324'))
MESSAGE = b'Hello, World!'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))

while True:
    print(sock.recv(64))
