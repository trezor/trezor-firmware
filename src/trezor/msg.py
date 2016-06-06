from TrezorMsg import Msg

_msg = Msg()


def setup(ifaces):
    return _msg.setup(ifaces)


def select(timeout_us):
    return _msg.select(timeout_us)


def send(iface, msg):
    return _msg.send(iface, msg)
