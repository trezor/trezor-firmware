#!/usr/bin/python
import os
import binascii
import argparse
import json
import threading

from trezorlib.client import TrezorClient, pin_func
from trezorlib.debuglink import DebugLink
from trezorlib.protobuf_json import pb2json
from trezorlib.pinmatrix import PinMatrixWidget

def parse_args(commands):
    parser = argparse.ArgumentParser(description='Commandline tool for Trezor devices.')
    parser.add_argument('-t', '--transport', dest='transport',  choices=['usb', 'serial', 'pipe', 'socket'], default='usb', help="Transport used for talking with the device")
    parser.add_argument('-p', '--path', dest='path', default='', help="Path used by the transport (usually serial port)")
    parser.add_argument('-dt', '--debuglink-transport', dest='debuglink_transport', choices=['usb', 'serial', 'pipe', 'socket'], default='usb', help="Debuglink transport")
    parser.add_argument('-dp', '--debuglink-path', dest='debuglink_path', default='', help="Path used by the transport (usually serial port)")
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

def get_transport(transport_string, path, **kwargs):
    if transport_string == 'usb':
        from trezorlib.transport_hid import HidTransport

        if path == '':
            try:
                path = list_usb()[0]
            except IndexError:
                raise Exception("No Trezor found on USB")

        return HidTransport(path, **kwargs)
 
    if transport_string == 'serial':
        from trezorlib.transport_serial import SerialTransport
        return SerialTransport(path, **kwargs)

    if transport_string == 'pipe':
        from trezorlib.transport_pipe import PipeTransport
        return PipeTransport(path, is_device=False, **kwargs)
    
    if transport_string == 'socket':
        from trezorlib.transport_socket import SocketTransportClient
        return SocketTransportClient(path, **kwargs)
    
    if transport_string == 'fake':
        from trezorlib.transport_fake import FakeTransport
        return FakeTransport(path, **kwargs)
    
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
        address_n = self.client.expand_path(args.n)
        return self.client.get_address(args.coin, address_n)
    
    def get_entropy(self, args):
        return binascii.hexlify(self.client.get_entropy(args.size))

    def get_features(self, args):
        return self.client.features

    def list_coins(self, args):
        return [ coin.coin_name for coin in self.client.features.coins ]

    def ping(self, args):
        return self.client.ping(args.msg)

    def get_public_node(self, args):
        address_n = self.client.expand_path(args.n)
        return self.client.get_public_node(address_n)
    
    def set_label(self, args):
        return self.client.apply_settings(label=args.label)

    def load_device(self, args):
        if not args.mnemonic and not args.xprv:
            raise Exception("Please provide mnemonic or xprv")

        if args.mnemonic:
            mnemonic = ' '.join(args.mnemonic)
            return self.client.load_device_by_mnemonic(mnemonic, args.pin, args.passphrase_protection, args.label)

        else:
            return self.client.load_device_by_xprv(args.xprv, args.pin, args.passphrase_protection, args.label)

    def reset_device(self, args):
        return self.client.reset_device(True, args.strength, args.passphrase, args.pin, args.label)

    def sign_message(self, args):
        return pb2json(self.client.sign_message(args.n, args.message), {'message': args.message})

    def verify_message(self, args):
        return self.client.verify_message(args.address, args.signature, args.message)

    def firmware_update(self, args):
        if not args.file:
            raise Exception("Must provide firmware filename")
        fp = open(args.file, 'r')
        if fp.read(4) != 'TRZR':
            raise Exception("Trezor firmware header expected")

        fp.seek(0)
        return self.client.firmware_update(fp=open(args.file, 'r'))

    list.help = 'List connected Trezor USB devices'
    ping.help = 'Send ping message'
    get_address.help = 'Get bitcoin address in base58 encoding'
    get_entropy.help = 'Get example entropy'
    get_features.help = 'Retrieve device features and settings'
    get_public_node.help = 'Get public node of given path'
    set_label.help = 'Set new wallet label'
    list_coins.help = 'List all supported coin types by the device'
    load_device.help = 'Load custom configuration to the device'
    reset_device.help = 'Perform factory reset of the device and generate new seed'
    sign_message.help = 'Sign message using address of given path'
    verify_message.help = 'Verify message'
    firmware_update.help = 'Upload new firmware to device (must be in bootloader mode)'

    get_address.arguments = (
        (('-c', '--coin'), {'type': str, 'default': 'Bitcoin'}),
        # (('n',), {'metavar': 'N', 'type': int, 'nargs': '+'}),
        (('-n', '-address'), {'type': str}),
    )
    
    get_entropy.arguments = (
        (('size',), {'type': int}),
    )

    get_features.arguments = ()

    list_coins.arguments = ()

    ping.arguments = (
        (('msg',), {'type': str}),
    )
    
    set_label.arguments = (
        (('label',), {'type': str}),
    )

    load_device.arguments = (
        (('-m', '--mnemonic'), {'type': str, 'nargs': '+'}),
        (('-x', '--xprv'), {'type': str}),
        (('-p', '--pin'), {'type': str, 'default': ''}),
        (('-r', '--passphrase-protection'), {'action': 'store_true', 'default': False}),
        (('-l', '--label'), {'type': str, 'default': ''}),
    )

    reset_device.arguments = (
        (('-t', '--strength'), {'type': int, 'choices': [128, 192, 256], 'default': 128}),
        (('-p', '--pin'), {'action': 'store_true', 'default': False}),
        (('-r', '--passphrase'), {'action': 'store_true', 'default': False}),
        (('-l', '--label'), {'type': str, 'default': ''}),
    )

    sign_message.arguments = (
        (('n',), {'metavar': 'N', 'type': int, 'nargs': '+'}),
        (('message',), {'type': str}),
    )

    verify_message.arguments = (
        (('address',), {'type': str}),
        (('signature',), {'type': str}),
        (('message',), {'type': str}),
    )

    get_public_node.arguments = (
        (('-n', '-address'), {'type': str}),
    )

    firmware_update.arguments = (
        (('-f', '--file'), {'type': str}),
    )

def list_usb():
    from trezorlib.transport_hid import HidTransport
    devices = HidTransport.enumerate()
    return devices

class PinMatrixThread(threading.Thread):
    '''
        Hacked PinMatrixWidget into command line tool :-).
    '''
    def __init__(self, input_text, message):
        super(PinMatrixThread, self).__init__()
        self.input_text = input_text
        self.message = message
        self.pin_value = ''

    def run(self):
        import sys
        from PyQt4.Qt import QApplication, QWidget, QVBoxLayout
        from PyQt4.QtGui import QPushButton, QLabel
        from PyQt4.QtCore import QObject, SIGNAL

        a = QApplication(sys.argv)

        matrix = PinMatrixWidget()

        def clicked():
            self.pin_value = str(matrix.get_value())
            a.closeAllWindows()

        ok = QPushButton('OK')
        QObject.connect(ok, SIGNAL('clicked()'), clicked)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.input_text + self.message))
        vbox.addWidget(matrix)
        vbox.addWidget(ok)

        w = QWidget()
        w.setLayout(vbox)
        w.move(100, 100)
        w.show()

        a.exec_()

def qt_pin_func(input_text, message=None):
    '''
        This is a hack to display Qt window in non-qt application.
        Qt window just asks for PIN and closes itself, which trigger join().
    '''
    if False:  # os.getenv('DISPLAY'):
        # Let's hope that system is configured properly and this won't crash
        t = PinMatrixThread(input_text, message)
        t.start()
        t.join()
        return t.pin_value
    else:
        # Most likely no X is running,
        # let's fallback to default pin_func implementation
        return pin_func(input_text, message)

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
        if args.debuglink_transport == 'usb' and args.debuglink_path == '':
            debuglink_transport = get_transport('usb', args.path, debug_link=True)
        else:
            debuglink_transport = get_transport(args.debuglink_transport, args.debuglink_path)
        debuglink = DebugLink(debuglink_transport)    
    else:
        debuglink = None
        
    client = TrezorClient(transport, pin_func=qt_pin_func, debuglink=debuglink)
    client.setup_debuglink(button=True, pin_correct=True)
    cmds = Commands(client)
    
    res = args.func(cmds, args)
    
    if args.json:
        print json.dumps(res, sort_keys=True, indent=4)
    else:
        print res
    
if __name__ == '__main__':
    main()
