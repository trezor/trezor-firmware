#!/usr/bin/python

import time

from transport_pipe import PipeTransport
from transport_serial import SerialTransport
from bitkey_proto import bitkey_pb2 as proto

def pprint(msg):
    return "<%s>:\n%s" % (msg.__class__.__name__, msg)

def call(msg, tries=3):
    print '----------------------'
    print "Sending", pprint(msg)
    d.write(msg)
    resp = d.read()
    
    if isinstance(resp, proto.OtpRequest):
        if resp.message:
            print "Message:", resp.message
        otp = raw_input("OTP required: ")
        d.write(proto.OtpAck(otp=otp))
        resp = d.read()

    if isinstance(resp, proto.PinRequest):
        if resp.message:
            print "Message:", resp.message
        pin = raw_input("PIN required: ")
        d.write(proto.PinAck(pin=pin))
        resp = d.read()
    
    if isinstance(resp, proto.Failure) and resp.code in (3, 6):
        if tries <= 1 and resp.code == 3:
            raise Exception("OTP is invalid, too many retries")
        if tries <= 1 and resp.code == 6:
            raise Exception("PIN is invalid, too many retries")
        
        # Invalid OTP or PIN, try again
        if resp.code == 3:
            print "OTP is invalid, let's try again..."
        elif resp.code == 6:
            print "PIN is invalid, let's try again..."
            
        return call(msg, tries-1)

    if isinstance(resp, proto.Failure):
        raise Exception(resp.code, resp.message)
    
    print "Received", pprint(resp)
    return resp
    
d = PipeTransport('../../bitkey-python/device.socket', is_device=False)
#d = SerialTransport('../../bitkey-python/COM9')

#start = time.time()

#for x in range(1000):

call(proto.Initialize())
call(proto.Ping())
call(proto.GetUUID())
#call(proto.GetEntropy(size=10))
#call(proto.LoadDevice(seed='beyond neighbor scratch swirl embarrass doll cause also stick softly physical nice',
#                      otp=True, pin='1234', spv=True))

#call(proto.ResetDevice())
call(proto.GetMasterPublicKey(algo=proto.ELECTRUM))
#call(proto.ResetDevice())
    
#print 10000 / (time.time() - start)
