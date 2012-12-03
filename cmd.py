#!/usr/bin/python
import binascii
import argparse
import json

import bitkeylib.bitkey_pb2 as proto
from bitkeylib.client import BitkeyClient
   
def parse_args(commands):
    parser = argparse.ArgumentParser(description='Commandline tool for Bitkey devices.')
    parser.add_argument('-a', '--algorithm', dest='algorithm', choices=['bip32', 'electrum'], default='bip32', help='Key derivation algorithm')
    parser.add_argument('-t', '--transport', dest='transport',  choices=['usb', 'serial', 'pipe', 'socket'], default='serial', help="Transport used for talking with the device")
    parser.add_argument('-p', '--path', dest='path', default='/dev/ttyAMA0', help="Path used by the transport (usually serial port)")
    parser.add_argument('-dt', '--debuglink-transport', dest='debuglink_transport', choices=['usb', 'serial', 'pipe', 'socket'], default='socket', help="Debuglink transport")
    parser.add_argument('-dp', '--debuglink-path', dest='debuglink_path', default='0.0.0.0:8001', help="Path used by the transport (usually serial port)")         
    parser.add_argument('-j', '--json', dest='json', action='store_true', help="Prints result as json object")
#    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Enable low-level debugging messages')

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
    
    return parser.parse_args()

def get_transport(transport_string, path):
    if transport_string == 'usb':
        raise NotImplemented("USB HID transport not implemented yet")
    
    if transport_string == 'serial':
        from bitkeylib.transport_serial import SerialTransport
        return SerialTransport(path)

    if transport_string == 'pipe':
        from bitkeylib.transport_pipe import PipeTransport
        return PipeTransport(path, is_device=False)
    
    if transport_string == 'socket':
        from bitkeylib.transport_socket import SocketTransport
        return SocketTransport(path, listen=False)
    
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
        
    def get_master_public_key(self, args):
        return 'ahoj'
    
    def get_entropy(self, args):
        return binascii.hexlify(self.client.get_entropy(args.size))
    
    get_entropy.help = 'Get example entropy'
    get_master_public_key.help = 'Get master public key'
    
    get_entropy.arguments = (
        (('size',), {'type': int}),
    )
    
def main():
    args = parse_args(Commands)
    
    transport = get_transport(args.transport, args.path)
    debuglink_transport = get_transport(args.debuglink_transport, args.debuglink_path)
    
    if args.algorithm == 'electrum':
        algo = proto.ELECTRUM
    elif args.algorithm == 'bip32':
        algo = proto.BIP32
    else:
        raise Exception("Unknown algorithm")
    
    client = BitkeyClient(transport, debuglink_transport, algo=algo)
    cmds = Commands(client)
    
    res = args.func(cmds, args)
    
    if args.json:
        print json.dumps(res)
    else:
        print res
    
if __name__ == '__main__':
    main()