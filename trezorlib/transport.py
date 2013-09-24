import struct
import mapping

class NotImplementedException(Exception):
    pass

class Transport(object):
    def __init__(self, device, *args, **kwargs):
        self.device = device
        self.session_depth = 0
        self._open()
    
    def _open(self):
        raise NotImplementedException("Not implemented")
    
    def _close(self):
        raise NotImplementedException("Not implemented")
    
    def _write(self, msg):
        raise NotImplementedException("Not implemented")
    
    def _read(self):
        raise NotImplementedException("Not implemented")
    
    def _session_begin(self):
        pass
    
    def _session_end(self):
        pass
    
    def ready_to_read(self):
        raise NotImplementedException("Not implemented")
    
    def session_begin(self):
        if self.session_depth == 0:
            self._session_begin()
        self.session_depth += 1
    
    def session_end(self):
        self.session_depth -= 1
        self.session_depth = max(0, self.session_depth)
        if self.session_depth == 0:
            self._session_end()
        
    def close(self):
        self._close()
        
    def write(self, msg):
        ser = msg.SerializeToString()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        self._write("##%s%s" % (header, ser))

    def read(self):
        if not self.ready_to_read():
            return None

        data = self._read()
        if data == None:
            return None
        
        return self._parse_message(data)
        
    def read_blocking(self):
        while True:
            data = self._read()
            if data != None:
                break
        
        return self._parse_message(data)

    def _parse_message(self, data):
        (msg_type, data) = data
        inst = mapping.get_class(msg_type)()
        inst.ParseFromString(data)
        return inst
    
    def _read_headers(self, read_f):
        # Try to read headers until some sane value are detected
        is_ok = False
        while not is_ok:

            # Align cursor to the beginning of the header ("##")
            c = read_f.read(1)
            i = 0
            while c != '#':
                i += 1
                if i >= 64:
                    # timeout
                    raise Exception("Timed out while waiting for the magic character")
                #print "Aligning to magic characters"
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
