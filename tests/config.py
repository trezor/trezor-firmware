import sys
sys.path = ['../',] + sys.path

from trezorlib.transport_pipe import PipeTransport
from trezorlib.transport_hid import HidTransport
from trezorlib.transport_socket import SocketTransportClient

use_real = False
use_pipe = True

if use_real:

    devices = HidTransport.enumerate()
    TRANSPORT = HidTransport
    TRANSPORT_ARGS = (devices[0], )
    TRANSPORT_KWARGS = {'debug_link': False}

    DEBUG_TRANSPORT = HidTransport
    DEBUG_TRANSPORT_ARGS = (devices[0], )
    DEBUG_TRANSPORT_KWARGS = {'debug_link': True}

elif use_pipe:

    TRANSPORT = PipeTransport
    TRANSPORT_ARGS = ('../../trezor-emu/pipe.trezor', False)
    TRANSPORT_KWARGS = {}

    DEBUG_TRANSPORT = PipeTransport
    DEBUG_TRANSPORT_ARGS = ('../../trezor-emu/pipe.trezor_debug', False)
    DEBUG_TRANSPORT_KWARGS = {}

else:

    devices = HidTransport.enumerate()
    TRANSPORT = HidTransport
    TRANSPORT_ARGS = (devices[0], )
    TRANSPORT_KWARGS = {'debug_link': False}

    DEBUG_TRANSPORT = SocketTransportClient
    DEBUG_TRANSPORT_ARGS = ('trezor.bo:2000', )
#    DEBUG_TRANSPORT_ARGS = ('trezor.dyn:2000')
    DEBUG_TRANSPORT_KWARGS = {}
