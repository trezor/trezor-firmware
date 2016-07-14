'''UDP Socket implementation of Transport.'''

import socket
from select import select
from .transport import TransportV2, ConnectionError

class UdpTransport(TransportV2):
    def __init__(self, device, *args, **kwargs):
        device = device.split(':')
        if len(device) < 2:
            if not device[0]:
                # Default port used by trezor v2
                device = ('127.0.0.1', 21324)
            else:
                device = ('127.0.0.1', int(device[0]))
        else:
            device = (device[0], int(device[1]))

        self.socket = None
        super(UdpTransport, self).__init__(device, *args, **kwargs)

    def _open(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(self.device)
        self.socket.settimeout(10)

    def _close(self):
        self.socket.close()
        self.socket = None

    def _ready_to_read(self):
        rlist, _, _ = select([self.socket], [], [], 0)
        return len(rlist) > 0

    def _write_chunk(self, chunk):
        if len(chunk) != 64:
            raise Exception("Unexpected data length")

        self.socket.sendall(chunk)

    def _read_chunk(self):
        while True:
            try:
                data = self.socket.recv(64)
                break
            except socket.timeout:
                continue
        if len(data) != 64:
            raise Exception("Unexpected chunk size: %d" % len(data))

        return bytearray(data)
