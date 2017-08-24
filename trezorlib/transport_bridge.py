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
from google.protobuf import json_format

from . import messages_pb2
from .transport import Transport

TREZORD_HOST = 'https://localback.net:21324'
CONFIG_URL = 'https://wallet.trezor.io/data/config_signed.bin'


def get_error(resp):
    return ' (error=%d str=%s)' % (resp.status_code, resp.json()['error'])


class BridgeTransport(Transport):
    '''
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    '''

    configured = False

    def __init__(self, device):
        super(BridgeTransport, self).__init__()

        self.device = device
        self.conn = requests.Session()
        self.session = None
        self.response = None

    def __str__(self):
        return self.device['path']

    @staticmethod
    def configure():
        if BridgeTransport.configured:
            return
        r = requests.get(CONFIG_URL, verify=False)
        if r.status_code != 200:
            raise Exception('Could not fetch config from %s' % CONFIG_URL)
        r = requests.post(TREZORD_HOST + '/configure', data=r.text)
        if r.status_code != 200:
            raise Exception('trezord: Could not configure' + get_error(r))
        BridgeTransport.configured = True

    @staticmethod
    def enumerate():
        BridgeTransport.configure()
        r = requests.get(TREZORD_HOST + '/enumerate')
        if r.status_code != 200:
            raise Exception('trezord: Could not enumerate devices' +
                            get_error(r))
        return [BridgeTransport(dev) for dev in r.json()]

    @staticmethod
    def find_by_path(path):
        for transport in BridgeTransport.enumerate():
            if path is None or transport.device['path'] == path:
                return transport
        raise Exception('Bridge device not found')

    def open(self):
        r = self.conn.post(TREZORD_HOST + '/acquire/%s' % self.device['path'])
        if r.status_code != 200:
            raise Exception('trezord: Could not acquire session' +
                            get_error(r))
        self.session = r.json()['session']

    def close(self):
        if not self.session:
            return
        r = self.conn.post(TREZORD_HOST + '/release/%s' % self.session)
        if r.status_code != 200:
            raise Exception('trezord: Could not release session' +
                            get_error(r))
        self.session = None

    def write(self, msg):
        msgname = msg.__class__.__name__
        msgjson = json_format.MessageToJson(
            msg, preserving_proto_field_name=True)
        payload = '{"type": "%s", "message": %s}' % (msgname, msgjson)
        r = self.conn.post(
            TREZORD_HOST + '/call/%s' % self.session, data=payload)
        if r.status_code != 200:
            raise Exception('trezord: Could not write message' + get_error(r))
        self.response = r.json()

    def read(self):
        if self.response is None:
            raise Exception('No response stored')
        msgtype = getattr(messages_pb2, self.response['type'])
        msg = msgtype()
        msg = json_format.ParseDict(self.response['message'], msg)
        self.response = None
        return msg
