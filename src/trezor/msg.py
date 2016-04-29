from TrezorMsg import Msg

_msg = Msg()

def select(timeout_ms):
    return _msg.select(timeout_ms)

def send(msg):
    return _msg.send(msg)
