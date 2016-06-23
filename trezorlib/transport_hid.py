'''USB HID implementation of Transport.'''

import hid
import time
from .transport import Transport, ConnectionError

DEVICE_IDS = [
    (0x534c, 0x0001),  # TREZOR
]

class FakeRead(object):
    # Let's pretend we have a file-like interface
    def __init__(self, func):
        self.func = func

    def read(self, size):
        return self.func(size)

class HidTransport(Transport):
    def __init__(self, device, *args, **kwargs):
        self.hid = None
        self.hid_version = None
        self.buffer = ''
        # self.read_timeout = kwargs.get('read_timeout')
        device = device[int(bool(kwargs.get('debug_link')))]
        super(HidTransport, self).__init__(device, *args, **kwargs)

    @classmethod
    def enumerate(cls):
        """
        Return a list of available TREZOR devices.
        """
        devices = {}
        for d in hid.enumerate(0, 0):
            vendor_id = d['vendor_id']
            product_id = d['product_id']
            serial_number = d['serial_number']
            interface_number = d['interface_number']
            path = d['path']

            # HIDAPI on Mac cannot detect correct HID interfaces, so device with
            # DebugLink doesn't work on Mac...
            if devices.get(serial_number) != None and devices[serial_number][0] == path:
                raise Exception("Two devices with the same path and S/N found. This is Mac, right? :-/")

            if (vendor_id, product_id) in DEVICE_IDS:
                devices.setdefault(serial_number, [None, None])
                if interface_number == 0 or interface_number == -1: # normal link
                    devices[serial_number][0] = path
                elif interface_number == 1: # debug link
                    devices[serial_number][1] = path
                else:
                    raise Exception("Unknown USB interface number: %d" % interface_number)

        # List of two-tuples (path_normal, path_debuglink)
        return list(devices.values())

    def is_connected(self):
        """
        Check if the device is still connected.
        """
        for d in hid.enumerate(0, 0):
            if d['path'] == self.device:
                return True
        return False

    def _open(self):
        self.buffer = bytearray()
        self.hid = hid.device()
        self.hid.open_path(self.device)
        self.hid.set_nonblocking(True)
        # determine hid_version
        r = self.hid.write([0, 63, ] + [0xFF] * 63)
        if r == 65:
            self.hid_version = 2
            return
        r = self.hid.write([63, ] + [0xFF] * 63)
        if r == 64:
            self.hid_version = 1
            return
        raise ConnectionError("Unknown HID version")

    def _close(self):
        self.hid.close()
        self.buffer = bytearray()
        self.hid = None

    def ready_to_read(self):
        return False

    def _write(self, msg, protobuf_msg):
        msg = bytearray(msg)
        while len(msg):
            if self.hid_version == 2:
                self.hid.write([0, 63, ] + list(msg[:63]) + [0] * (63 - len(msg[:63])))
            else:
                self.hid.write([63, ] + list(msg[:63]) + [0] * (63 - len(msg[:63])))
            msg = msg[63:]

    def _read(self):
        (msg_type, datalen) = self._read_headers(FakeRead(self._raw_read))
        return (msg_type, self._raw_read(datalen))

    def _raw_read(self, length):
        start = time.time()
        while len(self.buffer) < length:
            data = self.hid.read(64)
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
            self.buffer.extend(bytearray(data[1:]))

        ret = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return bytes(ret)
