'''BridgeTransport implements transport TREZOR Bridge (aka trezord).'''

import requests
import protobuf_json
import json
import mapping
from transport import Transport
import messages_pb2 as proto

TREZORD_HOST = 'http://localhost:21324'
CONFIG_URL = 'https://mytrezor.com/data/plugin/config_signed.bin'

def get_error(resp):
    return ' (error=%d str=%s)' % (resp.status_code, resp.json()['error'])

class BridgeTransport(Transport):
    def __init__(self, device, *args, **kwargs):

        r = requests.get(CONFIG_URL)
        if r.status_code != 200:
            raise Exception('Could not fetch config from %s' % CONFIG_URL)

        config = r.text

        r = requests.post(TREZORD_HOST + '/configure', data=config)
        if r.status_code != 200:
            raise Exception('trezord: Could not configure' + get_error(r))

        r = requests.get(TREZORD_HOST + '/enumerate')
        if r.status_code != 200:
            raise Exception('trezord: Could not enumerate devices' + get_error(r))
        enum = r.json()

        if len(enum) < 1:
            raise Exception('trezord: No devices found')

        self.path = enum[0]['path']
        self.session = None
        self.response = None

        super(BridgeTransport, self).__init__(device, *args, **kwargs)

    def _open(self):
        r = requests.post(TREZORD_HOST + '/acquire/%s' % self.path)
        if r.status_code != 200:
            raise Exception('trezord: Could not acquire session' + get_error(r))
        resp = r.json()
        self.session = resp['session']

    def _close(self):
        r = requests.post(TREZORD_HOST + '/release/%s' % self.session)
        if r.status_code != 200:
            raise Exception('trezord: Could not release session' + get_error(r))
        else:
            self.session = None

    def ready_to_read(self):
        return self.response != None

    def _write(self, msg, protobuf_msg):
        cls = protobuf_msg.__class__.__name__
        msg = protobuf_json.pb2json(protobuf_msg)
        payload = '{"type": "%s", "message": %s}' % (cls, json.dumps(msg))
        r = requests.post(TREZORD_HOST + '/call/%s' % self.session, data=payload)
        if r.status_code != 200:
            raise Exception('trezord: Could not write message' + get_error(r))
        else:
            self.response = r.json()

    def _read(self):
        if self.response == None:
            raise Exception('No response stored')
        cls = getattr(proto, self.response['type'])
        inst = cls()
        pb = protobuf_json.json2pb(inst, self.response['message'])
        return ('protobuf', pb)
