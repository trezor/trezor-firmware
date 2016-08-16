from __future__ import print_function

import sys
sys.path = ['../',] + sys.path

from trezorlib.transport_pipe import PipeTransport
from trezorlib.transport_hid import HidTransport

devices = HidTransport.enumerate()

if len(devices) > 0:
    if devices[0][1] != None:
        print('Using TREZOR')
        TRANSPORT = HidTransport
        TRANSPORT_ARGS = (devices[0],)
        TRANSPORT_KWARGS = {'debug_link': False}
        DEBUG_TRANSPORT = HidTransport
        DEBUG_TRANSPORT_ARGS = (devices[0],)
        DEBUG_TRANSPORT_KWARGS = {'debug_link': True}
    else:
        print('Using Raspberry Pi')
        TRANSPORT = HidTransport
        TRANSPORT_ARGS = (devices[0],)
        TRANSPORT_KWARGS = {'debug_link': False}
        DEBUG_TRANSPORT = SocketTransportClient
        DEBUG_TRANSPORT_ARGS = ('trezor.bo:2000',)
        DEBUG_TRANSPORT_KWARGS = {}
else:
    print('Using Emulator')
    TRANSPORT = PipeTransport
    TRANSPORT_ARGS = ('/tmp/pipe.trezor', False)
    TRANSPORT_KWARGS = {}
    DEBUG_TRANSPORT = PipeTransport
    DEBUG_TRANSPORT_ARGS = ('/tmp/pipe.trezor_debug', False)
    DEBUG_TRANSPORT_KWARGS = {}
