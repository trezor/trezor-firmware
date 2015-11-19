#!/usr/bin/env python
import os
import binascii
import argparse
import json
import base64
import urllib
import tempfile

from trezorlib.client import TrezorClient, TrezorClientDebug

def parse_args(commands):
    parser = argparse.ArgumentParser(description='Commandline tool for Trezor devices.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Prints communication to device')
    parser.add_argument('-t', '--transport', dest='transport',  choices=['usb', 'serial', 'pipe', 'socket', 'bridge'], default='usb', help="Transport used for talking with the device")
    parser.add_argument('-p', '--path', dest='path', default='', help="Path used by the transport (usually serial port)")
#    parser.add_argument('-dt', '--debuglink-transport', dest='debuglink_transport', choices=['usb', 'serial', 'pipe', 'socket'], default='usb', help="Debuglink transport")
#    parser.add_argument('-dp', '--debuglink-path', dest='debuglink_path', default='', help="Path used by the transport (usually serial port)")
    parser.add_argument('-j', '--json', dest='json', action='store_true', help="Prints result as json object")
#    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Enable low-level debugging')

    cmdparser = parser.add_subparsers(title='Available commands')

    for cmd in commands._list_commands():
        func = object.__getattribute__(commands, cmd)

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
                path = list_usb()[0][0]
            except IndexError:
                raise Exception("No Trezor found on USB")

        for d in HidTransport.enumerate():
            # Two-tuple of (normal_interface, debug_interface)
            if path in d:
                return HidTransport(d, **kwargs)

        raise Exception("Device not found")

    if transport_string == 'serial':
        from trezorlib.transport_serial import SerialTransport
        return SerialTransport(path, **kwargs)

    if transport_string == 'pipe':
        from trezorlib.transport_pipe import PipeTransport
        return PipeTransport(path, is_device=False, **kwargs)

    if transport_string == 'socket':
        from trezorlib.transport_socket import SocketTransportClient
        return SocketTransportClient(path, **kwargs)

    if transport_string == 'bridge':
        from trezorlib.transport_bridge import BridgeTransport
        return BridgeTransport(path, **kwargs)

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
        return self.client.get_address(args.coin, address_n, args.show_display)

    def get_entropy(self, args):
        return binascii.hexlify(self.client.get_entropy(args.size))

    def get_features(self, args):
        return self.client.features

    def list_coins(self, args):
        return [ coin.coin_name for coin in self.client.features.coins ]

    def ping(self, args):
        return self.client.ping(args.msg, button_protection=args.button_protection, pin_protection=args.pin_protection, passphrase_protection=args.passphrase_protection)

    def get_public_node(self, args):
        address_n = self.client.expand_path(args.n)
        return self.client.get_public_node(address_n, args.ecdsa_curve_name, args.show_display)

    def set_label(self, args):
        return self.client.apply_settings(label=args.label)

    def set_homescreen(self,args):
        if args.filename:
            from PIL import Image
            im = Image.open(args.filename)
            if im.size != (128,64):
                raise Exception('Wrong size of the image')
            im = im.convert('1')
            pix = im.load()
            img = ''
            for j in range(64):
                for i in range(128):
                    img += '1' if pix[i, j] else '0'
            img = ''.join(chr(int(img[i:i + 8], 2)) for i in range(0, len(img), 8))
        else:
            img = '\x00'
        return self.client.apply_settings(homescreen=img)

    def clear_session(self, args):
        return self.client.clear_session()

    def change_pin(self, args):
        return self.client.change_pin(args.remove)

    def wipe_device(self, args):
        return self.client.wipe_device()

    def recovery_device(self, args):
        return self.client.recovery_device(args.words, args.passphrase_protection,
                                    args.pin_protection, args.label, 'english')

    def load_device(self, args):
        if not args.mnemonic and not args.xprv:
            raise Exception("Please provide mnemonic or xprv")

        if args.mnemonic:
            mnemonic = ' '.join(args.mnemonic)
            return self.client.load_device_by_mnemonic(mnemonic, args.pin,
                        args.passphrase_protection, args.label, 'english', args.skip_checksum)

        else:
            return self.client.load_device_by_xprv(args.xprv, args.pin,
                        args.passphrase_protection, args.label, 'english')

    def reset_device(self, args):
        return self.client.reset_device(True, args.strength, args.passphrase_protection,
                                        args.pin_protection, args.label, 'english')

    def sign_message(self, args):
        address_n = self.client.expand_path(args.n)
        ret = self.client.sign_message(args.coin, address_n, args.message)
        output = {
            'message': args.message,
            'address': ret.address,
            'signature': base64.b64encode(ret.signature)
        }
        return output

    def verify_message(self, args):
        signature = base64.b64decode(args.signature)
        return self.client.verify_message(args.address, signature, args.message)

    def encrypt_message(self, args):
        pubkey = binascii.unhexlify(args.pubkey)
        address_n = self.client.expand_path(args.n)
        ret = self.client.encrypt_message(pubkey, args.message, args.display_only, args.coin, address_n)
        output = {
            'nonce': binascii.hexlify(ret.nonce),
            'message': binascii.hexlify(ret.message),
            'hmac': binascii.hexlify(ret.hmac),
            'payload': base64.b64encode(ret.nonce + ret.message + ret.hmac),
        }
        return output

    def decrypt_message(self, args):
        address_n = self.client.expand_path(args.n)
        payload = base64.b64decode(args.payload)
        nonce, message, msg_hmac = payload[:33], payload[33:-8], payload[-8:]
        ret = self.client.decrypt_message(address_n, nonce, message, msg_hmac)
        return ret

    def encrypt_keyvalue(self, args):
        address_n = self.client.expand_path(args.n)
        ret = self.client.encrypt_keyvalue(address_n, args.key, args.value)
        return binascii.hexlify(ret)

    def decrypt_keyvalue(self, args):
        address_n = self.client.expand_path(args.n)
        ret = self.client.decrypt_keyvalue(address_n, args.key, args.value.decode("hex"))
        return ret

    def firmware_update(self, args):
        if args.file:
            fp = open(args.file, 'r')
        elif args.url:
            print "Downloading from", args.url
            resp = urllib.urlretrieve(args.url)
            fp = open(resp[0], 'r')
            urllib.urlcleanup() # We still keep file pointer open
        else:
            resp = urllib.urlopen("https://mytrezor.com/data/firmware/releases.json")
            releases = json.load(resp)
            version = lambda r: r['version']
            version_string = lambda r: ".".join(map(str, version(r)))
            if args.version:
                release = next((r for r in releases if version_string(r) == args.version))
            else:
                release = max(releases, key=version)
                print "No file, url, or version given. Fetching latest version: %s" % version_string(release)
            print "Firmware fingerprint: %s" % release['fingerprint']
            args.url = release['url']
            return self.firmware_update(args)

        if fp.read(8) == '54525a52':
            print "Converting firmware to binary"

            fp.seek(0)
            fp_old = fp

            fp = tempfile.TemporaryFile()
            fp.write(binascii.unhexlify(fp_old.read()))

            fp_old.close()

        fp.seek(0)
        if fp.read(4) != 'TRZR':
            raise Exception("Trezor firmware header expected")

        print "Please confirm action on device..."

        fp.seek(0)
        return self.client.firmware_update(fp=fp)

    list.help = 'List connected Trezor USB devices'
    ping.help = 'Send ping message'
    get_address.help = 'Get bitcoin address in base58 encoding'
    get_entropy.help = 'Get example entropy'
    get_features.help = 'Retrieve device features and settings'
    get_public_node.help = 'Get public node of given path'
    set_label.help = 'Set new wallet label'
    set_homescreen.help = 'Set new homescreen'
    clear_session.help = 'Clear session (remove cached PIN, passphrase, etc.)'
    change_pin.help = 'Change new PIN or remove existing'
    list_coins.help = 'List all supported coin types by the device'
    wipe_device.help = 'Reset device to factory defaults and remove all private data.'
    recovery_device.help = 'Start safe recovery workflow'
    load_device.help = 'Load custom configuration to the device'
    reset_device.help = 'Perform device setup and generate new seed'
    sign_message.help = 'Sign message using address of given path'
    verify_message.help = 'Verify message'
    encrypt_message.help = 'Encrypt message'
    decrypt_message.help = 'Decrypt message'
    encrypt_keyvalue.help = 'Encrypt value by given key and path'
    decrypt_keyvalue.help = 'Decrypt value by given key and path'
    firmware_update.help = 'Upload new firmware to device (must be in bootloader mode)'

    get_address.arguments = (
        (('-c', '--coin'), {'type': str, 'default': 'Bitcoin'}),
        (('-n', '-address'), {'type': str}),
        (('-d', '--show-display'), {'action': 'store_true', 'default': False}),
    )

    get_entropy.arguments = (
        (('size',), {'type': int}),
    )

    get_features.arguments = ()

    list_coins.arguments = ()

    ping.arguments = (
        (('msg',), {'type': str}),
        (('-b', '--button-protection'), {'action': 'store_true', 'default': False}),
        (('-p', '--pin-protection'), {'action': 'store_true', 'default': False}),
        (('-r', '--passphrase-protection'), {'action': 'store_true', 'default': False}),
    )

    set_label.arguments = (
        (('-l', '--label',), {'type': str, 'default': ''}),
#        (('-c', '--clear'), {'action': 'store_true', 'default': False})
    )

    set_homescreen.arguments = (
        (('-f', '--filename',), {'type': str, 'default': ''}),
    )
    change_pin.arguments = (
         (('-r', '--remove'), {'action': 'store_true', 'default': False}),
    )

    wipe_device.arguments = ()

    recovery_device.arguments = (
        (('-w', '--words'), {'type': int}),
        (('-p', '--pin-protection'), {'action': 'store_true', 'default': False}),
        (('-r', '--passphrase-protection'), {'action': 'store_true', 'default': False}),
        (('-l', '--label'), {'type': str, 'default': ''}),
    )

    load_device.arguments = (
        (('-m', '--mnemonic'), {'type': str, 'nargs': '+'}),
        (('-x', '--xprv'), {'type': str}),
        (('-p', '--pin'), {'type': str, 'default': ''}),
        (('-r', '--passphrase-protection'), {'action': 'store_true', 'default': False}),
        (('-l', '--label'), {'type': str, 'default': ''}),
        (('-s', '--skip-checksum'), {'action': 'store_true', 'default': False}),
    )

    reset_device.arguments = (
        (('-t', '--strength'), {'type': int, 'choices': [128, 192, 256], 'default': 256}),
        (('-p', '--pin-protection'), {'action': 'store_true', 'default': False}),
        (('-r', '--passphrase-protection'), {'action': 'store_true', 'default': False}),
        (('-l', '--label'), {'type': str, 'default': ''}),
    )

    sign_message.arguments = (
        (('-c', '--coin'), {'type': str, 'default': 'Bitcoin'}),
        (('-n', '-address'), {'type': str}),
        (('message',), {'type': str}),
    )

    encrypt_message.arguments = (
        (('pubkey',), {'type': str}),
        (('message',), {'type': str}),
        (('-d', '--display-only'), {'action': 'store_true', 'default': False}),
        (('-c', '--coin'), {'type': str, 'default': 'Bitcoin'}),
        (('-n', '-address'), {'type': str}),
    )

    decrypt_message.arguments = (
        (('-n', '-address'), {'type': str}),
        (('payload',), {'type': str}),
    )

    verify_message.arguments = (
        (('address',), {'type': str}),
        (('signature',), {'type': str}),
        (('message',), {'type': str}),
    )

    encrypt_keyvalue.arguments = (
        (('-n', '-address'), {'type': str}),
        (('key',), {'type': str}),
        (('value',), {'type': str}),
    )

    decrypt_keyvalue.arguments = (
        (('-n', '-address'), {'type': str}),
        (('key',), {'type': str}),
        (('value',), {'type': str}),
    )

    get_public_node.arguments = (
        (('-n', '-address'), {'type': str}),
        (('-e', '--ecdsa-curve-name'), {'type': str}),
        (('-d', '--show-display'), {'action': 'store_true', 'default': False}),
    )

    firmware_update.arguments = (
        (('-f', '--file'), {'type': str}),
        (('-u', '--url'), {'type': str}),
        (('-n', '--version'), {'type': str}),
    )

def list_usb():
    from trezorlib.transport_hid import HidTransport
    return HidTransport.enumerate()

'''
class PinMatrixThread(threading.Thread):
    # Hacked PinMatrixWidget into command line tool :-).
    def __init__(self, input_text, message):
        super(PinMatrixThread, self).__init__()
        self.input_text = input_text
        self.message = message
        self.pin_value = ''

    def run(self):
        from trezorlib.pinmatrix import PinMatrixWidget

        import sys
        from PyQt4.Qt import QApplication, QWidget, QVBoxLayout
        from PyQt4.QtGui import QPushButton, QLabel
        from PyQt4.QtCore import QObject, SIGNAL

        a = QApplication(sys.argv)
pass
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
    # This is a hack to display Qt window in non-qt application.
    # Qt window just asks for PIN and closes itself, which trigger join().
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
'''

def main():
    args = parse_args(Commands)

    if args.cmd == 'list':
        devices = list_usb()
        if args.json:
            print json.dumps(devices)
        else:
            for dev in devices:
                if dev[1] != None:
                    print "%s - debuglink enabled" % dev[0]
                else:
                    print dev[0]
        return

    transport = get_transport(args.transport, args.path)
    if args.verbose:
        client = TrezorClientDebug(transport)
    else:
        client = TrezorClient(transport)

    cmds = Commands(client)

    res = args.func(cmds, args)

    if args.json:
        print json.dumps(res, sort_keys=True, indent=4)
    else:
        print res

if __name__ == '__main__':
    main()
