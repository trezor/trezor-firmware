'''USB HID implementation of Transport.'''

import hid
import time
from transport import Transport, NotImplementedException

DEVICE_IDS = [
    (0x1cbe, 0xcaf3), # Trezor
    (0x10c4, 0xea80), # Trezor Pi
    (0x08f7, 0x0002), # EasyTemp
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
        super(HidTransport, self).__init__(device, *args, **kwargs)

    @classmethod
    def enumerate(cls):
        devices = []
        for d in hid.enumerate(0, 0):
            vendor_id = d.get('vendor_id')
            product_id = d.get('product_id')
            serial_number = d.get('serial_number')
            
            if (vendor_id, product_id) in DEVICE_IDS:
                devices.append("0x%04x:0x%04x:%s" % (vendor_id, product_id, serial_number))
                
        return devices
        
    def _open(self):
        self.buffer = ''
        path = self.device.split(':')
        self.hid = hid.device(int(path[0], 16), int(path[1], 16))#, path[2])
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
