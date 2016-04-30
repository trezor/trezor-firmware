'''UDP Socket implementation of Transport.'''

import socket
from select import select
import time
from transport import Transport, ConnectionError

class FakeRead(object):
    # Let's pretend we have a file-like interface
    def __init__(self, func):
        self.func = func

    def read(self, size):
        return self.func(size)

class UdpTransport(Transport):
    def __init__(self, device, *args, **kwargs):
        self.buffer = ''

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

    def _close(self):
        self.socket.close()
        self.socket = None
        self.buffer = ''

    def ready_to_read(self):
        rlist, _, _ = select([self.socket], [], [], 0)
        return len(rlist) > 0

    def _write(self, msg, protobuf_msg):
        msg = bytearray(msg)
        while len(msg):
            # Report ID, data padded to 63 bytes
            self.socket.sendall(chr(63) + msg[:63] + b'\0' * (63 - len(msg[:63])))
            msg = msg[63:]

    def _read(self):
        (msg_type, datalen) = self._read_headers(FakeRead(self._raw_read))
        return (msg_type, self._raw_read(datalen))

    def _raw_read(self, length):
        start = time.time()
        while len(self.buffer) < length:
            data = self.socket.recv(64)
            if not len(data):
                if time.time() - start > 10:
                    # Over 10 s of no response, let's check if
                    # device is still alive
                    if not self.is_connected():
                        raise ConnectionError("Connection failed")
                    else:
                        # Restart timer
                        start = time.time()

                time.sleep(0.001)
                continue

            report_id = data[0]

            if report_id > 63:
                # Command report
                raise Exception("Not implemented")

            # Payload received, skip the report ID
            self.buffer += str(bytearray(data[1:]))

        ret = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return ret
