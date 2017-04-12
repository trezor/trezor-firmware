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

'''USB HID implementation of Transport.'''

import hid
import time
from .transport import TransportV1, TransportV2, ConnectionError

def enumerate():
    """
    Return a list of available TREZOR devices.
    """
    devices = {}
    for d in hid.enumerate(0, 0):
        vendor_id = d['vendor_id']
        product_id = d['product_id']
        serial_number = d['serial_number']
        interface_number = d['interface_number']
        usage_page = d['usage_page']
        path = d['path']

        if (vendor_id, product_id) in DEVICE_IDS:
            devices.setdefault(serial_number, [None, None])
            # first match by usage_page, then try interface number
            if usage_page == 0xFF00 or interface_number == 0:  # normal link
                devices[serial_number][0] = path
            elif usage_page == 0xFF01 or interface_number == 1:  # debug link
                devices[serial_number][1] = path

    # List of two-tuples (path_normal, path_debuglink)
    return sorted(devices.values())

def path_to_transport(path):
    try:
        device = [ d for d in hid.enumerate(0, 0) if d['path'] == path ][0]
    except IndexError:
        raise ConnectionError("Connection failed")

    # VID/PID found, let's find proper transport
    try:
        transport = DEVICE_TRANSPORTS[(device['vendor_id'], device['product_id'])]
    except IndexError:
        raise Exception("Unknown transport for VID:PID %04x:%04x" % (vid, pid))

    return transport

class _HidTransport(object):
    def __init__(self, device, *args, **kwargs):
        self.hid = None
        self.hid_version = None

        device = device[int(bool(kwargs.get('debug_link')))]
        super(_HidTransport, self).__init__(device, *args, **kwargs)

    def is_connected(self):
        """
        Check if the device is still connected.
        """
        for d in hid.enumerate(0, 0):
            if d['path'] == self.device:
                return True
        return False

    def _open(self):
        self.hid = hid.device()
        self.hid.open_path(self.device)
        self.hid.set_nonblocking(True)

        # determine hid_version
        if isinstance(self, HidTransportV2):
            self.hid_version = 2
        else:
            r = self.hid.write([0, 63, ] + [0xFF] * 63)
            if r == 65:
                self.hid_version = 2
                return
            r = self.hid.write([63, ] + [0xFF] * 63)
            if r == 64:
                self.hid_version = 1
                return
            raise ConnectionError("Unknown HID version")

    def _close(self):
        self.hid.close()
        self.hid = None

    def _write_chunk(self, chunk):
        if len(chunk) != 64:
            raise Exception("Unexpected data length")

        if self.hid_version == 2:
            self.hid.write(b'\0' + chunk)
        else:
            self.hid.write(chunk)

    def _read_chunk(self):
        start = time.time()

        while True:
            data = self.hid.read(64)
            if not len(data):
                if time.time() - start > 10:
                    # Over 10 s of no response, let's check if
                    # device is still alive
                    if not self.is_connected():
                        raise ConnectionError("Connection failed")

                    # Restart timer
                    start = time.time()

                time.sleep(0.001)
                continue

            break

        if len(data) != 64:
            raise Exception("Unexpected chunk size: %d" % len(data))

        return bytearray(data)

class HidTransportV1(_HidTransport, TransportV1):
    pass

class HidTransportV2(_HidTransport, TransportV2):
    pass

DEVICE_IDS = [
    (0x534c, 0x0001),  # TREZOR
    (0x1209, 0x53c0),  # TREZORv2 Bootloader
    (0x1209, 0x53c1),  # TREZORv2
]

DEVICE_TRANSPORTS = {
    (0x534c, 0x0001): HidTransportV1,  # TREZOR
    (0x1209, 0x53c0): HidTransportV1,  # TREZORv2 Bootloader
    (0x1209, 0x53c1): HidTransportV2,  # TREZORv2
}

# Backward compatible wrapper, decides for proper transport
# based on VID/PID of given path
def HidTransport(device, *args, **kwargs):
    transport = path_to_transport(device[0])
    return transport(device, *args, **kwargs)

# Backward compatibility hack; HidTransport is a function, not a class like before
HidTransport.enumerate = enumerate
