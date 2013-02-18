import bitkey_pb2 as proto
from transport import NotImplementedException

def otp_info(otp):
    print "Device asks for OTP %s" % otp.otp
    
def pin_info(pin):
    print "Device asks for PIN %s" % pin.pin

def button_press(yes_no):
    print "User pressed", '"y"' if yes_no else '"n"'
    
class DebugLink(object):
    def __init__(self, transport, otp_func=otp_info, pin_func=pin_info, button_func=button_press):
        self.transport = transport

        self.otp_func = otp_func
        self.pin_func = pin_func
        self.button_func = button_func
            
    def get_state(self, otp=False, pin=False):
        self.transport.write(proto.DebugLinkGetState(otp=otp, pin=pin))
        return self.transport.read_blocking()

    def load_device(self, seed, otp, pin, spv):
        self.transport.write(proto.LoadDevice(seed=seed, otp=otp, pin=pin, spv=spv))
        resp = self.transport.read_blocking()
        return isinstance(resp, proto.Success)        
            
    def read_otp(self):
        obj = self.get_state(otp=True).otp
        print "Read OTP:", obj.otp
        self.otp_func(obj)
        return obj

    def read_pin(self):
        obj = self.get_state(pin=True).pin
        print "Read PIN:", obj.pin
        self.pin_func(obj)
        return obj
    
    def press_button(self, yes_no):
        print "Pressing", yes_no
        self.button_func(yes_no)
        self.transport.write(proto.DebugLinkDecision(yes_no=yes_no))

    def press_yes(self):
        self.press_button(True)
    
    def press_no(self):
        self.press_button(False)