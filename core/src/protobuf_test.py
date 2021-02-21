from trezorutils import protobuf_decode
from trezor.utils import BufferWriter
from trezor.messages.Ping import Ping
import protobuf


def dump_message(msg):
    length = protobuf.count_message(msg)
    buffer = bytearray(length)
    protobuf.dump_message(BufferWriter(buffer), msg)
    return buffer


m = Ping(message="ahoj")
x = dump_message(m)
y = protobuf_decode(x, m.MESSAGE_WIRE_TYPE)

print(y)