from TrezorMsg import Msg

_msg = Msg()


def set_interfaces(ifaces):
    return _msg.set_interfaces(ifaces)


def get_interfaces():
    return _msg.get_interfaces()


def select(timeout_us):
    return _msg.select(timeout_us)


def send(iface, msg):
    return _msg.send(iface, msg)
