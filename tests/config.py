import sys
sys.path = ['../',] + sys.path

from bitkeylib.transport_pipe import PipeTransport

TRANSPORT = PipeTransport
TRANSPORT_ARGS = ('../../bitkey-python/device.socket', False)

DEBUG_TRANSPORT = PipeTransport
DEBUG_TRANSPORT_ARGS = ('../../bitkey-python/device.socket.debug', False)