from trezor.loop import wait


class MockHID:
    def __init__(self, num):
        self.num = num
        self.data = []

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)

    def wait_object(self, mode):
        return wait(mode | self.num)
