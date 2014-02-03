'''USB HID implementation of Transport.'''

import hid
import time
import platform
from transport import Transport, NotImplementedException

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
        device = device[int(bool(kwargs.get('debug_link')))]
        super(HidTransport, self).__init__(device, *args, **kwargs)

    @classmethod
    def _detect_debuglink(cls, path):
        # Takes platform-specific path of USB and
        # decide if the HID interface is normal transport
        # or debuglink
        
        if platform.system() in ('Linux', 'Darwin'):
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

        else:
            raise Exception("USB interface detection not implemented for %s" % platform.system())

    @classmethod
    def enumerate(cls):
        devices = {}
        for d in hid.enumerate(0, 0):
            vendor_id = d['vendor_id']
            product_id = d['product_id']
            serial_number = d['serial_number']
            path = d['path']

            if (vendor_id, product_id) in DEVICE_IDS:
                devices.setdefault(serial_number, [None, None])
                devices[serial_number][int(bool(cls._detect_debuglink(path)))] = path
                
        # List of two-tuples (path_normal, path_debuglink)
        return devices.values()
        
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
    
    def _write(self, msg):
        msg = bytearray(msg)
        while len(msg):            
            # Report ID, data padded to 63 bytes
            self.hid.write([63, ] + list(msg[:63]) + [0] * (63 - len(msg[:63])))
            msg = msg[63:]
            
    def _read(self):
        (msg_type, datalen) = self._read_headers(FakeRead(self._raw_read))
        return (msg_type, self._raw_read(datalen))
                    
    def _raw_read(self, length):        
        while len(self.buffer) < length:
            data = self.hid.read(64)
            if not len(data):
                time.sleep(0.05)
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
