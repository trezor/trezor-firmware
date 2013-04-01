#!/usr/bin/python
import binascii
import argparse
import json

import bitkeylib.bitkey_pb2 as proto
from bitkeylib.client import BitkeyClient
from bitkeylib.debuglink import DebugLink
   
def parse_args(commands):
    parser = argparse.ArgumentParser(description='Commandline tool for Bitkey devices.')
    parser.add_argument('-a', '--algorithm', dest='algorithm', choices=['bip32', 'electrum'], default='bip32', help='Key derivation algorithm')
    parser.add_argument('-t', '--transport', dest='transport',  choices=['usb', 'serial', 'pipe', 'socket'], default='serial', help="Transport used for talking with the device")
    parser.add_argument('-p', '--path', dest='path', default='/dev/ttyAMA0', help="Path used by the transport (usually serial port)")
    parser.add_argument('-dt', '--debuglink-transport', dest='debuglink_transport', choices=['usb', 'serial', 'pipe', 'socket'], default='socket', help="Debuglink transport")
    parser.add_argument('-dp', '--debuglink-path', dest='debuglink_path', default='0.0.0.0:8001', help="Path used by the transport (usually serial port)")         
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

    def get_master_public_key(self, args):
        return binascii.hexlify(self.client.get_master_public_key())
    
    def get_uuid(self, args):
        return binascii.hexlify(self.client.get_uuid())
        
    def load_device(self, args):
        seed = ' '.join(args.seed)

        return self.client.load_device(seed, args.otp, args.pin, args.spv) 
        
    list.help = 'List connected Trezor USB devices'
    get_address.help = 'Get bitcoin address in base58 encoding'
    get_entropy.help = 'Get example entropy'
    get_uuid.help = 'Get device\'s unique identifier'
    get_master_public_key.help = 'Get master public key'
    load_device.help = 'Load custom configuration to the device'
    
    get_address.arguments = (
        (('n',), {'metavar': 'N', 'type': int, 'nargs': '+'}),
    )
    
    get_entropy.arguments = (
        (('size',), {'type': int}),
    )
    
    load_device.arguments = (
        (('-s', '--seed'), {'type': str, 'nargs': '+'}),
        (('-n', '--pin'), {'type': str, 'default': ''}),
        (('-o', '--otp'), {'action': 'store_true'}),
        (('-p', '--spv'), {'action': 'store_true'}),
    )
    
def main():
    args = parse_args(Commands)

    if args.cmd == 'list':
        from bitkeylib.transport_hid import HidTransport
        devices = HidTransport.enumerate()
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
    
    if args.algorithm == 'electrum':
        algo = proto.ELECTRUM
    elif args.algorithm == 'bip32':
        algo = proto.BIP32
    else:
        raise Exception("Unknown algorithm")
    
    client = BitkeyClient(transport, debuglink=debuglink, algo=algo)
    client.setup_debuglink(button=True, otp_correct=True, pin_correct=True)
    cmds = Commands(client)
    
    res = args.func(cmds, args)
    
    if args.json:
        print json.dumps(res)
    else:
        print res
    
if __name__ == '__main__':
    main()
