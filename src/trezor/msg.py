from TrezorMsg import Msg, USB, HID, VCP

_msg = Msg()


def init_usb(usb, ifaces):
    return _msg.init_usb(usb, ifaces)


def select(timeout_us):
    return _msg.select(timeout_us)


def send(iface, msg):
    return _msg.send(iface, msg)
