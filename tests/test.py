#!/usr/bin/python
import sys
sys.path = ['../',] + sys.path

import time

from bitkeylib.transport_pipe import PipeTransport
from bitkeylib.transport_serial import SerialTransport
import bitkeylib.bitkey_pb2 as proto

from bitkeylib.client import BitkeyClient

bitkey = BitkeyClient('../../bitkey-python/device.socket', debug=True)
bitkey.open()
bitkey.call(proto.Ping(message='ahoj!'))
bitkey.call(proto.SetMaxFeeKb(maxfee_kb=200000))
bitkey.close()

'''
d = PipeTransport('../bitkey-python/device.socket', is_device=False)
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
''' 

#print 10000 / (time.time() - start)
