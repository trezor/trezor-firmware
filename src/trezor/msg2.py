import sys

if sys.platform == 'linux':
    import transport_pipe as pipe

    def write(msg):
        return pipe.write(msg)
        
    def read():
        return pipe.read()

    def set_notify(_on_read):
        return pipe.set_notify(_on_read)

    pipe.init('../pipe')

else:
    NotImplemented("HID transport")
