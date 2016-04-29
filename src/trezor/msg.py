from TrezorMsg import Msg

_msg = Msg()

def select(timeout_us):
    return _msg.select(timeout_us)

def send(msg):
    return _msg.send(msg)
