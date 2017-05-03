# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import sys
sys.path = ['../../'] + sys.path


try:
    from trezorlib.transport_hid import HidTransport
    HID_ENABLED = True
except Exception as e:
    print('HID transport disabled:', e.message, e.args)
    HID_ENABLED = False

try:
    from trezorlib.transport_pipe import PipeTransport
    PIPE_ENABLED = True
except Exception as e:
    print('PIPE transport disabled:', e.message, e.args)
    PIPE_ENABLED = False

try:
    from trezorlib.transport_udp import UdpTransport
    UDP_ENABLED = True
except Exception as e:
    print('UDP transport disabled:', e.message, e.args)
    UDP_ENABLED = False


def pipe_exists(path):
    import os, stat
    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except:
        return False


if HID_ENABLED and len(HidTransport.enumerate()) > 0:

    devices = HidTransport.enumerate()
    print('Using TREZOR')
    TRANSPORT = HidTransport
    TRANSPORT_ARGS = (devices[0],)
    TRANSPORT_KWARGS = {'debug_link': False}
    DEBUG_TRANSPORT = HidTransport
    DEBUG_TRANSPORT_ARGS = (devices[0],)
    DEBUG_TRANSPORT_KWARGS = {'debug_link': True}

elif PIPE_ENABLED and pipe_exists('/tmp/pipe.trezor.to'):

    print('Using Emulator (v1=pipe)')
    TRANSPORT = PipeTransport
    TRANSPORT_ARGS = ('/tmp/pipe.trezor', False)
    TRANSPORT_KWARGS = {}
    DEBUG_TRANSPORT = PipeTransport
    DEBUG_TRANSPORT_ARGS = ('/tmp/pipe.trezor_debug', False)
    DEBUG_TRANSPORT_KWARGS = {}

elif UDP_ENABLED:

    print('Using Emulator (v2=udp)')
    TRANSPORT = UdpTransport
    TRANSPORT_ARGS = ('', )
    TRANSPORT_KWARGS = {}
    DEBUG_TRANSPORT = UdpTransport
    DEBUG_TRANSPORT_ARGS = ('', )
    DEBUG_TRANSPORT_KWARGS = {}
