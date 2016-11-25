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
import os
from select import select
from .transport import TransportV1

"""PipeTransport implements fake wire transport over local named pipe.
Use this transport for talking with trezor simulator."""

class PipeTransport(TransportV1):
    def __init__(self, device, is_device, *args, **kwargs):
        self.is_device = is_device # Set True if act as device

        super(PipeTransport, self).__init__(device, *args, **kwargs)

    def _open(self):
        if self.is_device:
            self.filename_read = self.device+'.to'
            self.filename_write = self.device+'.from'

            os.mkfifo(self.filename_read, 0o600)
            os.mkfifo(self.filename_write, 0o600)
        else:
            self.filename_read = self.device+'.from'
            self.filename_write = self.device+'.to'

            if not os.path.exists(self.filename_write):
                raise Exception("Not connected")

        self.write_fd = os.open(self.filename_write, os.O_RDWR)#|os.O_NONBLOCK)
        self.write_f = os.fdopen(self.write_fd, 'w+b', 0)

        self.read_fd = os.open(self.filename_read, os.O_RDWR)#|os.O_NONBLOCK)
        self.read_f = os.fdopen(self.read_fd, 'rb', 0)

    def _close(self):
        self.read_f.close()
        self.write_f.close()
        if self.is_device:
            os.unlink(self.filename_read)
            os.unlink(self.filename_write)

    def _ready_to_read(self):
        rlist, _, _ = select([self.read_f], [], [], 0)
        return len(rlist) > 0

    def _write_chunk(self, chunk):
        if len(chunk) != 64:
            raise Exception("Unexpected data length")

        try:
            self.write_f.write(chunk)
            self.write_f.flush()
        except OSError:
            print("Error while writing to socket")
            raise

    def _read_chunk(self):
        while True:
            try:
                data = self.read_f.read(64)
            except IOError:
                print("Failed to read from device")
                raise

            if not len(data):
                time.sleep(0.001)
                continue

            break

        if len(data) != 64:
            raise Exception("Unexpected chunk size: %d" % len(data))

        return bytearray(data)
