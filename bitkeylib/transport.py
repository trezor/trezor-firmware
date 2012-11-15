import struct
import bitkey_pb2 as proto
import mapping

class Transport(object):
    def __init__(self, device, *args, **kwargs):
        self.device = device
        self._open()
    
    def _open(self):
        raise NotImplemented
    
    def _close(self):
        raise NotImplemented
    
    def _write(self, msg):
        raise NotImplemented
    
    def _read(self):
        raise NotImplemented
    
    def ready_to_read(self):
        raise NotImplemented
        
    def close(self):
        self._close()
        
    def write(self, msg):
        ser = msg.SerializeToString()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        self._write("##%s%s" % (header, ser))

    def read(self):
        (msg_type, data) = self._read()
        inst = mapping.get_class(msg_type)()
        inst.ParseFromString(data)
        return inst
    
    def _read_headers(self, read_f):
        # Try to read headers until some sane value are detected
        is_ok = False
        while not is_ok:

            # Align cursor to the beginning of the header ("##")
            c = read_f.read(1)
            while c != '#':
                if c == '':
                    # timeout
                    raise Exception("Timed out while waiting for the magic character")
                print "Warning: Aligning to magic characters"
                c = read_f.read(1)

            if read_f.read(1) != "#":
                # Second character must be # to be valid header
                raise Exception("Second magic character is broken")

            # Now we're most likely on the beginning of the header
            try:
                headerlen = struct.calcsize(">HL")
                (msg_type, datalen) = struct.unpack(">HL", read_f.read(headerlen))
                break
            except:
                raise Exception("Cannot parse header length")
       
        return (msg_type, datalen)
