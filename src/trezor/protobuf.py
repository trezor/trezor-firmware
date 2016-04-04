from TrezorProtobuf import Protobuf

_protobuf = Protobuf()

def encode(data):
    return _protobuf.encode(data)

def decode(data):
    return _protobuf.decode(data)
