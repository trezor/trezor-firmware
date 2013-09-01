import sys
sys.path = ['../',] + sys.path

from bitkeylib.transport_pipe import PipeTransport
from bitkeylib.transport_hid import HidTransport
from bitkeylib.transport_socket import SocketTransportClient

TRANSPORT = PipeTransport
TRANSPORT_ARGS = ('../../trezor-emu/pipe.trezor', False)

#TRANSPORT = HidTransport
#TRANSPORT_ARGS = ('0x10c4:0xea80:000868D3', False)

#TRANSPORT = SocketTransportClient
#TRANSPORT_ARGS = ('trezor.dyn:3000', False)

DEBUG_TRANSPORT = PipeTransport
DEBUG_TRANSPORT_ARGS = ('../../trezor-emu/pipe.trezor_debug', False)

#DEBUG_TRANSPORT = SocketTransportClient
#DEBUG_TRANSPORT_ARGS = ('trezor.dyn:2000', False)
