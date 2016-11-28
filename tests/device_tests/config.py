from __future__ import print_function

import sys
sys.path = ['../../'] + sys.path

from trezorlib.transport_pipe import PipeTransport
from trezorlib.transport_hid import HidTransport
from trezorlib.transport_udp import UdpTransport

def pipe_exists(path):
    import os
    try:
        os.stat(path)
        return True
    except:
        return False

devices = HidTransport.enumerate()

if len(devices) > 0:
    print('Using TREZOR')
    TRANSPORT = HidTransport
    TRANSPORT_ARGS = (devices[0],)
    TRANSPORT_KWARGS = {'debug_link': False}
    DEBUG_TRANSPORT = HidTransport
    DEBUG_TRANSPORT_ARGS = (devices[0],)
    DEBUG_TRANSPORT_KWARGS = {'debug_link': True}

elif pipe_exists('/tmp/pipe.trezor.to'):
    print('Using Emulator (v1=pipe)')
    TRANSPORT = PipeTransport
    TRANSPORT_ARGS = ('/tmp/pipe.trezor', False)
    TRANSPORT_KWARGS = {}
    DEBUG_TRANSPORT = PipeTransport
    DEBUG_TRANSPORT_ARGS = ('/tmp/pipe.trezor_debug', False)
    DEBUG_TRANSPORT_KWARGS = {}

elif True:
    print('Using Emulator (v2=udp)')
    TRANSPORT = UdpTransport
    TRANSPORT_ARGS = ('', )
    TRANSPORT_KWARGS = {}
    DEBUG_TRANSPORT = UdpTransport
    DEBUG_TRANSPORT_ARGS = ('', )
    DEBUG_TRANSPORT_KWARGS = {}
