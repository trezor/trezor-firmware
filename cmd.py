#!/usr/bin/python
import binascii
import argparse
import json

from bitkeylib.client import BitkeyClient
from bitkeylib.debuglink import DebugLink
from bitkeylib.protobuf_json import pb2json

def parse_args(commands):
    parser = argparse.ArgumentParser(description='Commandline tool for Bitkey devices.')
    parser.add_argument('-t', '--transport', dest='transport',  choices=['usb', 'serial', 'pipe', 'socket'], default='usb', help="Transport used for talking with the device")
    parser.add_argument('-p', '--path', dest='path', default='', help="Path used by the transport (usually serial port)")
    parser.add_argument('-dt', '--debuglink-transport', dest='debuglink_transport', choices=['usb', 'serial', 'pipe', 'socket'], default='socket', help="Debuglink transport")
    parser.add_argument('-dp', '--debuglink-path', dest='debuglink_path', default='127.0.0.1:2000', help="Path used by the transport (usually serial port)")         
    parser.add_argument('-j', '--json', dest='json', action='store_true', help="Prints result as json object")
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Enable low-level debugging')

    cmdparser = parser.add_subparsers(title='Available commands')
    
    for cmd in commands._list_commands():
        func = object.__getattribute__(commands, cmd)
        try:
            help = func.help
        except AttributeError:
            help = ''
            
        try:
            arguments = func.arguments
        except AttributeError:
            arguments = ((('params',), {'nargs': '*'}),)
        
        item = cmdparser.add_parser(cmd, help=func.help)
        for arg in arguments:
            item.add_argument(*arg[0], **arg[1])
            
        item.set_defaults(func=func)
        item.set_defaults(cmd=cmd)
    
    return parser.parse_args()

def get_transport(transport_string, path):
    if transport_string == 'usb':
        from bitkeylib.transport_hid import HidTransport

        if path == '':
            try:
                path = list_usb()[0]
            except IndexError:
                raise Exception("No Trezor found on USB")

        return HidTransport(path)
 
    if transport_string == 'serial':
        from bitkeylib.transport_serial import SerialTransport
        return SerialTransport(path)

    if transport_string == 'pipe':
        from bitkeylib.transport_pipe import PipeTransport
        return PipeTransport(path, is_device=False)
    
    if transport_string == 'socket':
        from bitkeylib.transport_socket import SocketTransportClient
        return SocketTransportClient(path)
    
    if transport_string == 'fake':
        from bitkeylib.transport_fake import FakeTransport
        return FakeTransport(path)
    
    raise NotImplemented("Unknown transport")

class Commands(object):
    def __init__(self, client):
        self.client = client
        
    @classmethod
    def _list_commands(cls):
        return [ x for x in dir(cls) if not x.startswith('_') ]
  
    def list(self, args):
        # Fake method for advertising 'list' command
        pass
 
    def get_address(self, args):
        return self.client.get_address(args.n)
    
    def get_entropy(self, args):
        return binascii.hexlify(self.client.get_entropy(args.size))

    def get_features(self, args):
        return pb2json(self.client.features)

    def ping(self, args):
        return self.client.ping(args.msg)

    def get_master_public_key(self, args):
        return binascii.hexlify(self.client.get_master_public_key())
    
    def get_serial_number(self, args):
        return binascii.hexlify(self.client.get_serial_number())

    def set_label(self, args):
        return self.client.apply_settings(label=args.label)

    def set_coin(self, args):
        return self.client.apply_settings(coin_shortcut=args.coin_shortcut)

    def load_device(self, args):
        seed = ' '.join(args.seed)

        return self.client.load_device(seed, args.pin) 
        
    list.help = 'List connected Trezor USB devices'
    ping.help = 'Send ping message'
    get_address.help = 'Get bitcoin address in base58 encoding'
    get_entropy.help = 'Get example entropy'
    get_features.help = 'Retrieve device features and settings'
    get_serial_number.help = 'Get device\'s unique identifier'
    get_master_public_key.help = 'Get master public key'
    set_label.help = 'Set new wallet label'
    set_coin.help = 'Switch device to another crypto currency'
    load_device.help = 'Load custom configuration to the device'
    
    get_address.arguments = (
        (('n',), {'metavar': 'N', 'type': int, 'nargs': '+'}),
    )
    
    get_entropy.arguments = (
        (('size',), {'type': int}),
    )

    get_features.arguments = ()

    ping.arguments = (
        (('msg',), {'type': str}),
    )
    
    set_label.arguments = (
        (('label',), {'type': str}),
    )

    set_coin.arguments = (
        (('coin_shortcut',), {'type': str}),
    )

    load_device.arguments = (
        (('-s', '--seed'), {'type': str, 'nargs': '+'}),
        (('-n', '--pin'), {'type': str, 'default': ''}),
    )

def list_usb():
    from bitkeylib.transport_hid import HidTransport
    devices = HidTransport.enumerate()
    return devices
  
def main():
    args = parse_args(Commands)

    if args.cmd == 'list':
        devices = list_usb()
        if args.json:
            print json.dumps(devices)
        else:
            for dev in devices:
                print dev
        return

    transport = get_transport(args.transport, args.path)
    if args.debug:
        debuglink_transport = get_transport(args.debuglink_transport, args.debuglink_path)
        debuglink = DebugLink(debuglink_transport)    
    else:
        debuglink = None
        
    client = BitkeyClient(transport, debuglink=debuglink)
    client.setup_debuglink(button=True, pin_correct=True)
    cmds = Commands(client)
    
    res = args.func(cmds, args)
    
    if args.json:
        print json.dumps(res, sort_keys=True, indent=4)
    else:
        print res
    
if __name__ == '__main__':
    main()
