class Mutex:
    def __init__(self):
        self.ifaces = []
        self.busy = None

    def add(self, iface_num: int):
        if iface_num not in self.ifaces:
            self.ifaces.append(iface_num)

    def set_busy(self, iface_num: int):
        if iface_num in self.ifaces:
            self.busy = iface_num

    def get_busy(self, iface_num: int) -> int:
        return (
            iface_num in self.ifaces
            and self.busy is not None
            and self.busy != iface_num
        )

    def release(self, iface_num: int):
        if iface_num == self.busy:
            self.busy = None
