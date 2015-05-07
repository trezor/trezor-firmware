'''USB HID implementation of Transport.'''

import hid
import time
import platform
from transport import Transport, ConnectionError, NotImplementedException

DEVICE_IDS = [
    (0x10c4, 0xea80),  # Shield
    (0x534c, 0x0001),  # Trezor
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
        self.buffer = ''
        # self.read_timeout = kwargs.get('read_timeout')
        device = device[int(bool(kwargs.get('debug_link')))]
        super(HidTransport, self).__init__(device, *args, **kwargs)

    @classmethod
    def _detect_debuglink(cls, path):
        # Takes platform-specific path of USB and
        # decide if the HID interface is normal transport
        # or debuglink
        
        if platform.system() == 'Linux':
            # Sample: 0003:0017:00
            if path.endswith(':00'):
                return False
            return True
        
        elif platform.system() == 'Windows':
            # Sample: \\\\?\\hid#vid_534c&pid_0001&mi_01#7&1d71791f&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}
            # Note: 'mi' parameter is optional and might be unset
            if '&mi_01#' in path:  # ,,,<o.O>,,,~
                return True
            return False

        elif platform.system() == 'Darwin':
            # DebugLink doesn't work on Mac
            return False

        else:
            raise Exception("USB interface detection not implemented for %s" % platform.system())

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
            path = d['path']

            # HIDAPI on Mac cannot detect correct HID interfaces, so device with
            # DebugLink doesn't work on Mac...
            if devices.get(serial_number) != None and devices[serial_number][0] == path:
                raise Exception("Two devices with the same path and S/N found. This is Mac, right? :-/")

            if (vendor_id, product_id) in DEVICE_IDS:
                devices.setdefault(serial_number, [None, None])
                devices[serial_number][int(bool(cls._detect_debuglink(path)))] = path
                
        # List of two-tuples (path_normal, path_debuglink)
        return devices.values()

    def is_connected(self):
        """
        Check if the device is still connected.
        """
        for d in hid.enumerate(0, 0):
            if d['path'] == self.device:
                return True
        return False
        
    def _open(self):
        self.buffer = ''
        self.hid = hid.device()
        self.hid.open_path(self.device)
        self.hid.set_nonblocking(True)
        self.hid.send_feature_report([0x41, 0x01]) # enable UART
        self.hid.send_feature_report([0x43, 0x03]) # purge TX/RX FIFOs
    
    def _close(self):
        self.hid.close()
        self.buffer = ''
        self.hid = None
    
    def ready_to_read(self):
        return False
    
    def _write(self, msg, protobuf_msg):
        msg = bytearray(msg)
        while len(msg):            
            # Report ID, data padded to 63 bytes
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
            self.buffer += str(bytearray(data[1:]))

        ret = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return ret
