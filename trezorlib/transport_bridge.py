# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016      Jochen Hoenicke <hoenicke@gmail.com>
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

from __future__ import absolute_import

import requests
import binascii
from io import BytesIO
import struct

from . import mapping
from . import messages
from . import protobuf
from .transport import Transport, TransportException

TREZORD_HOST = 'http://127.0.0.1:21325'


def get_error(resp):
    return ' (error=%d str=%s)' % (resp.status_code, resp.json()['error'])


class BridgeTransport(Transport):
    '''
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    '''

    PATH_PREFIX = 'bridge'
    HEADERS = {'Origin': 'https://python.trezor.io'}

    def __init__(self, device):
        super(BridgeTransport, self).__init__()

        self.device = device
        self.conn = requests.Session()
        self.session = None
        self.response = None

    def __str__(self):
        return self.get_path()

    def get_path(self):
        return '%s:%s' % (self.PATH_PREFIX, self.device['path'])

    @classmethod
    def enumerate(cls):
        try:
            r = requests.post(TREZORD_HOST + '/enumerate', headers=cls.HEADERS)
            if r.status_code != 200:
                raise TransportException('trezord: Could not enumerate devices' + get_error(r))
            return [BridgeTransport(dev) for dev in r.json()]
        except:
            return []

    @classmethod
    def find_by_path(cls, path):
        if isinstance(path, bytes):
            path = path.decode()
        path = path.replace('%s:' % cls.PATH_PREFIX, '')

        for transport in BridgeTransport.enumerate():
            if path is None or transport.device['path'] == path:
                return transport
        raise TransportException('Bridge device not found')

    def open(self):
        r = self.conn.post(TREZORD_HOST + '/acquire/%s/null' % self.device['path'], headers=self.HEADERS)
        if r.status_code != 200:
            raise TransportException('trezord: Could not acquire session' + get_error(r))
        self.session = r.json()['session']

    def close(self):
        if not self.session:
            return
        r = self.conn.post(TREZORD_HOST + '/release/%s' % self.session, headers=self.HEADERS)
        if r.status_code != 200:
            raise TransportException('trezord: Could not release session' + get_error(r))
        self.session = None

    def write(self, msg):
        data = BytesIO()
        protobuf.dump_message(data, msg)
        ser = data.getvalue()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        data = binascii.hexlify(header + ser).decode()
        r = self.conn.post(
            TREZORD_HOST + '/call/%s' % self.session, data=data, headers=self.HEADERS)
        if r.status_code != 200:
            raise TransportException('trezord: Could not write message' + get_error(r))
        self.response = r.text

    def read(self):
        if self.response is None:
            raise TransportException('No response stored')
        data = binascii.unhexlify(self.response)
        headerlen = struct.calcsize('>HL')
        (msg_type, datalen) = struct.unpack('>HL', data[:headerlen])
        data = BytesIO(data[headerlen:headerlen + datalen])
        msg = protobuf.load_message(data, mapping.get_class(msg_type))
        self.response = None
        return msg
