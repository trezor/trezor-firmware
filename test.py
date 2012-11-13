#!/usr/bin/python

import time

from transport_pipe import PipeTransport
from transport_serial import SerialTransport
from bitkey_proto import bitkey_pb2 as proto

from client import BitkeyClient

bitkey = BitkeyClient('../bitkey-python/device.socket', debug=True)
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
