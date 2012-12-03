import bitkey_pb2 as proto
 
def otp_info(otp):
    print "Device asks for OTP %s" % otp
    
def pin_info(pin):
    print "Device asks for PIN %s" % pin

def button_press(yes_no):
    print "User pressed", '"y"' if yes_no else '"n"'
    
class DebugLink(object):
    def __init__(self, transport, otp_func=otp_info, pin_func=pin_info, button_func=button_press):
        self.transport = transport
        self.otp_func = otp_func
        self.pin_func = pin_func
        self.button_func = button_func
            
    def read_otp(self):
        obj = self.transport.read()
        if not isinstance(obj, proto.OtpAck):
            raise Exception("Expected OtpAck object, got %s" % obj)
        self.otp_func(obj)
        return obj

    def read_pin(self):
        obj = self.transport.read()
        if not isinstance(obj, proto.PinAck):
            raise Exception("Expected PinAck object, got %s" % obj)
        self.pin_func(obj)
        return obj
    
    def press_button(self, yes_no):
        self.button_func(yes_no)
        self.transport.write(proto.DebugLinkDecision(yes_no=yes_no))
        #obj = self.transport.read()
        #if not isinstance(obj, proto.Success):
        #    raise Exception("Expected Success object, got %s" % obj)
        
    def press_yes(self):
        self.press_button(True)
    
    def press_no(self):
        self.press_button(False)