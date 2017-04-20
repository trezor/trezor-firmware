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

'''BridgeTransport implements transport TREZOR Bridge (aka trezord).'''

import json
import requests
from . import protobuf_json
from . import messages_pb2 as proto
from .transport import TransportV1

TREZORD_HOST = 'https://localback.net:21324'
CONFIG_URL = 'https://wallet.trezor.io/data/config_signed.bin'

def get_error(resp):
    return ' (error=%d str=%s)' % (resp.status_code, resp.json()['error'])

class BridgeTransport(TransportV1):
    CONFIGURED = False

    def __init__(self, device, *args, **kwargs):
        self.configure()

        self.path = device['path']

        self.session = None
        self.response = None
        self.conn = requests.Session()

        super(BridgeTransport, self).__init__(device, *args, **kwargs)

    @staticmethod
    def configure():
        if BridgeTransport.CONFIGURED: return
        r = requests.get(CONFIG_URL, verify=False)
        if r.status_code != 200:
            raise Exception('Could not fetch config from %s' % CONFIG_URL)

        config = r.text

        r = requests.post(TREZORD_HOST + '/configure', data=config)
        if r.status_code != 200:
            raise Exception('trezord: Could not configure' + get_error(r))
        BridgeTransport.CONFIGURED = True

    @classmethod
    def enumerate(cls):
        """
        Return a list of available TREZOR devices.
        """
        cls.configure()
        r = requests.get(TREZORD_HOST + '/enumerate')
        if r.status_code != 200:
            raise Exception('trezord: Could not enumerate devices' + get_error(r))

        enum = r.json()

        return enum

    def _open(self):
        r = self.conn.post(TREZORD_HOST + '/acquire/%s' % self.path)
        if r.status_code != 200:
            raise Exception('trezord: Could not acquire session' + get_error(r))
        resp = r.json()
        self.session = resp['session']

    def _close(self):
        r = self.conn.post(TREZORD_HOST + '/release/%s' % self.session)
        if r.status_code != 200:
            raise Exception('trezord: Could not release session' + get_error(r))
        else:
            self.session = None

    def _ready_to_read(self):
        return self.response != None

    def write(self, protobuf_msg):
        # Override main 'write' method, HTTP transport cannot be
        # splitted to chunks
        cls = protobuf_msg.__class__.__name__
        msg = protobuf_json.pb2json(protobuf_msg)
        payload = '{"type": "%s", "message": %s}' % (cls, json.dumps(msg))
        r = self.conn.post(TREZORD_HOST + '/call/%s' % self.session, data=payload)
        if r.status_code != 200:
            raise Exception('trezord: Could not write message' + get_error(r))
        else:
            self.response = r.json()

    def _read(self):
        if self.response is None:
            raise Exception('No response stored')
        cls = getattr(proto, self.response['type'])
        inst = cls()
        pb = protobuf_json.json2pb(inst, self.response['message'])
        return (0, 'protobuf', pb)
