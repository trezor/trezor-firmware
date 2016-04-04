import sys

if sys.platform == 'linux':
    import transport_pipe as pipe

    def send(msg):
        return pipe.write(msg)
        
    def read():
        return pipe.read()

    def set_notify(_on_read):
        return pipe.set_notify(_on_read)

    pipe.init('../pipe')

else:
    from TrezorMsg import Msg

    def send(msg):
        return Msg.send(msg)

    def read():
        raise NotImplemented
        return Msg.receive()

    def set_notify(_on_read):
        raise NotImplemented
