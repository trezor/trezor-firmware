'''USB HID implementation of Transport.'''

import hid
from transport import Transport, NotImplementedException

DEVICE_IDS = [
    (0x1cbe, 0xcaf3), # Trezor
    (0x10c4, 0xea80), # Trezor Pi
    (0x08f7, 0x0002), # EasyTemp
]

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
                devices.append((vendor_id, product_id, serial_number))
                
        return devices
    
    def _open(self):
        self.buffer = ''
        self.hid = hid.device(self.device[0], self.device[1])#, self.device[2])
    
    def _close(self):
        self.hid.close()
        self.buffer = ''
        self.hid = None
    
    def ready_to_read(self):
        return False
    
    def _write(self, msg):
        msg = bytearray(msg)
        while len(msg):
            to_send = min(63, len(msg))
            
            #print [to_send,] + list(msg[:to_send])
            self.hid.write([to_send,] + list(msg[:to_send]))
            
            msg = msg[to_send:]
            
    def _read(self):
        (msg_type, datalen) = self._read_headers(self._raw_read)
        return (msg_type, self._raw_read(datalen))
                    
    def _raw_read(self, length):        
        while len(self.buffer) < length:
            data = self.hid.read(64)
            report_id = data[0]
            
            if report_id > 63:
                # Command report
                raise Exception("Not implemented")
                            
            # Payload received
            self.buffer += str(bytearray(data[1:report_id+1]))

        ret = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return ret