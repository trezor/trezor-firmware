import messages_pb2 as proto
from transport import NotImplementedException

def pin_info(pin):
    print "Device asks for PIN %s" % pin

def button_press(yes_no):
    print "User pressed", '"y"' if yes_no else '"n"'

class DebugLink(object):
    def __init__(self, transport, pin_func=pin_info, button_func=button_press):
        self.transport = transport

        self.pin_func = pin_func
        self.button_func = button_func

    def close(self):
        self.transport.close()
        
    def read_pin(self):
        self.transport.write(proto.DebugLinkGetState())
        obj = self.transport.read_blocking()
        print "Read PIN:", obj.pin
        print "Read matrix:", obj.matrix

        return (obj.pin, obj.matrix)

    def read_pin_encoded(self):
        pin, matrix = self.read_pin()

        # Now we have real PIN and PIN matrix.
        # We have to encode that into encoded pin,
        # because application must send back positions
        # on keypad, not a real PIN.
        pin_encoded = ''.join([ str(matrix.index(p) + 1) for p in pin])

        print "Encoded PIN:", pin_encoded
        self.pin_func(pin_encoded)

        return pin_encoded

    def read_layout(self):
        self.transport.write(proto.DebugLinkGetState())
        obj = self.transport.read_blocking()
        return obj.layout

    def read_mnemonic(self):
        self.transport.write(proto.DebugLinkGetState())
        obj = self.transport.read_blocking()
        return obj.mnemonic

    def read_node(self):
        self.transport.write(proto.DebugLinkGetState())
        obj = self.transport.read_blocking()
        return obj.node

    def press_button(self, yes_no):
        print "Pressing", yes_no
        self.button_func(yes_no)
        self.transport.write(proto.DebugLinkDecision(yes_no=yes_no))

    def press_yes(self):
        self.press_button(True)

    def press_no(self):
        self.press_button(False)

    def stop(self):
        self.transport.write(proto.DebugLinkStop())
