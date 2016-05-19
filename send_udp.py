#!/usr/bin/python
import socket
import os
from binascii import unhexlify

UDP_IP = os.getenv('TREZOR_UDP_IP', '127.0.0.1')
UDP_PORT = int(os.getenv('TREZOR_UDP_PORT', '21324'))

INITIALIZE = b'?##\x00\x00\x00\x00\x00\x00'
GET_PUBLIC_KEY = b'?##\x00\x0b\x00\x00\x00\r\x12\tsecp256k1\x18\x00'
PIN_MATRIX_ACK = b'?##\x00\x13\x00\x00\x00\x05\n\x03268'

messages = [
    INITIALIZE,
    # GET_PUBLIC_KEY,
    # PIN_MATRIX_ACK,
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(messages.pop(0), (UDP_IP, UDP_PORT))

while True:
    print(sock.recv(64))
