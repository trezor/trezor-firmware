from trezor.loop import wait


class MockHID:

    TX_PACKET_LEN = 64
    RX_PACKET_LEN = 64

    def __init__(self, num):
        self.num = num
        self.data = []
        self.packet = None

    def pad_packet(self, data):
        if len(data) > self.RX_PACKET_LEN:
            raise Exception("Too long packet")
        padding_length = self.RX_PACKET_LEN - len(data)
        return data + b"\x00" * padding_length

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)

    def mock_read(self, packet, gen):
        self.packet = self.pad_packet(packet)
        return gen.send(self.RX_PACKET_LEN)

    def read(self, buffer, offset=0):
        if self.packet is None:
            raise Exception("No packet to read")

        if offset > len(buffer):
            raise Exception("Offset out of bounds")

        buffer_space = len(buffer) - offset

        if len(self.packet) > buffer_space:
            raise Exception("Buffer too small")
        else:
            end = offset + len(self.packet)
            buffer[offset:end] = self.packet
            read = len(self.packet)
            self.packet = None
            return read

    def wait_object(self, mode):
        return wait(mode | self.num)
