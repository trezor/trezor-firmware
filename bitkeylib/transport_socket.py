'''SocketTransport implements TCP socket interface for Transport.'''

import socket
from select import select
from transport import Transport

class FakeRead(object):
    # Because socket is the only transport which don't implement read()
    
    def __init__(self, socket):
        self.socket = socket
        
    def read(self, size):
        return self.socket.recv(size)

class SocketTransportClient(Transport):
    def __init__(self, device, *args, **kwargs):
        device = device.split(':')
        if len(device) < 2:
            device = ('0.0.0.0', int(device[0]))
        else:
            device = (device[0], int(device[1]))

        self.socket = None        
        super(SocketTransportClient, self).__init__(device, *args, **kwargs)
    
    def _open(self):
        print self.device
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.device)
        self.filelike = self.socket.makefile()
        
    def _close(self):
        self.socket.close()
        self.socket = None
        self.filelike = None
    
    def ready_to_read(self):
        rlist, _, _ = select([self.socket], [], [], 0)
        return len(rlist) > 0        
    
    def _write(self, msg):
        self.socket.sendall(msg)
        
    def _read(self):
        try:
            print 'filelike', self.filelike
            (msg_type, datalen) = self._read_headers(self.filelike)
            return (msg_type, self.filelike.read(datalen))
        except socket.error:
            print "Failed to read from device"
            raise

class SocketTransport(Transport):
    def __init__(self, device, *args, **kwargs):
        device = device.split(':')
        if len(device) < 2:
            device = ('0.0.0.0', int(device[0]))
        else:
            device = (device[0], int(device[1]))

        self.socket = None
        self.client = None
        self.filelike = None

        super(SocketTransport, self).__init__(device, *args, **kwargs)
        
    def _open(self):
        print self.device

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self.socket.setblocking(0)
        
        self.socket.bind(self.device)
        self.socket.listen(1)
        
    def _disconnect_client(self):
        if self.client != None:
            self.client = None
            self.filelike = None
    
    def _close(self):
        self._disconnect_client()
        self.socket.close()
        self.socket = None
        
    def ready_to_read(self):
        if self.client:
            # Connected
            rlist, _, _ = select([self.client], [], [], 0)
            return len(rlist) > 0
        else:
            # Waiting for connection
            rlist, _, _ = select([self.socket], [], [], 0)
            if len(rlist) > 0:
                (self.client, _) = self.socket.accept()
                print "Connected", self.client
                self.filelike = self.client.makefile()#FakeRead(self.client)#self.client.makefile()
                return self.ready_to_read()
            return False
        
    
    def _write(self, msg):
        if self.filelike:
            # None on disconnected client
            self.filelike.write(msg)
            self.filelike.flush()
        
    def _read(self):
        try:
            print 'filelike', self.filelike
            (msg_type, datalen) = self._read_headers(self.filelike)
            x = (msg_type, self.filelike.read(datalen))
            print x
            return x
        except socket.error:
            print "Failed to read from device"
            raise
        except Exception:
            self._disconnect_client()
            return None