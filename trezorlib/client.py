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

import functools
import logging
import os
import sys
import time
import binascii
import hashlib
import unicodedata
import getpass
import warnings

from mnemonic import Mnemonic

from . import messages as proto
from . import tools
from . import mapping
from . import nem
from . import protobuf
from . import stellar
from .debuglink import DebugLink

if sys.version_info.major < 3:
    raise Exception("Trezorlib does not support Python 2 anymore.")


SCREENSHOT = False
LOG = logging.getLogger(__name__)

# make a getch function
try:
    import termios
    import tty
    # POSIX system. Create and return a getch that manipulates the tty.
    # On Windows, termios will fail to import.

    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

except ImportError:
    # Windows system.
    # Use msvcrt's getch function.
    import msvcrt

    def getch():
        while True:
            key = msvcrt.getch()
            if key in (0x00, 0xe0):
                # skip special keys: read the scancode and repeat
                msvcrt.getch()
                continue
            return key.decode('latin1')


def get_buttonrequest_value(code):
    # Converts integer code to its string representation of ButtonRequestType
    return [k for k in dir(proto.ButtonRequestType) if getattr(proto.ButtonRequestType, k) == code][0]


class CallException(Exception):
    pass


class PinException(CallException):
    pass


class field:
    # Decorator extracts single value from
    # protobuf object. If the field is not
    # present, raises an exception.
    def __init__(self, field):
        self.field = field

    def __call__(self, f):
        @functools.wraps(f)
        def wrapped_f(*args, **kwargs):
            ret = f(*args, **kwargs)
            return getattr(ret, self.field)
        return wrapped_f


class expect:
    # Decorator checks if the method
    # returned one of expected protobuf messages
    # or raises an exception
    def __init__(self, *expected):
        self.expected = expected

    def __call__(self, f):
        @functools.wraps(f)
        def wrapped_f(*args, **kwargs):
            ret = f(*args, **kwargs)
            if not isinstance(ret, self.expected):
                raise RuntimeError("Got %s, expected %s" % (ret.__class__, self.expected))
            return ret
        return wrapped_f


def session(f):
    # Decorator wraps a BaseClient method
    # with session activation / deactivation
    @functools.wraps(f)
    def wrapped_f(*args, **kwargs):
        __tracebackhide__ = True  # pytest traceback hiding - this function won't appear in tracebacks
        client = args[0]
        client.transport.session_begin()
        try:
            return f(*args, **kwargs)
        finally:
            client.transport.session_end()
    return wrapped_f


def normalize_nfc(txt):
    '''
    Normalize message to NFC and return bytes suitable for protobuf.
    This seems to be bitcoin-qt standard of doing things.
    '''
    if isinstance(txt, bytes):
        txt = txt.decode('utf-8')
    return unicodedata.normalize('NFC', txt).encode('utf-8')


class BaseClient(object):
    # Implements very basic layer of sending raw protobuf
    # messages to device and getting its response back.
    def __init__(self, transport, **kwargs):
        LOG.info("creating client instance for device: {}".format(transport.get_path()))
        self.transport = transport
        super(BaseClient, self).__init__()  # *args, **kwargs)

    def close(self):
        pass

    def cancel(self):
        self.transport.write(proto.Cancel())

    @session
    def call_raw(self, msg):
        __tracebackhide__ = True  # pytest traceback hiding - this function won't appear in tracebacks
        self.transport.write(msg)
        return self.transport.read()

    @session
    def call(self, msg):
        resp = self.call_raw(msg)
        handler_name = "callback_%s" % resp.__class__.__name__
        handler = getattr(self, handler_name, None)

        if handler is not None:
            msg = handler(resp)
            if msg is None:
                raise ValueError("Callback %s must return protobuf message, not None" % handler)
            resp = self.call(msg)

        return resp

    def callback_Failure(self, msg):
        if msg.code in (proto.FailureType.PinInvalid,
                        proto.FailureType.PinCancelled, proto.FailureType.PinExpected):
            raise PinException(msg.code, msg.message)

        raise CallException(msg.code, msg.message)

    def register_message(self, msg):
        '''Allow application to register custom protobuf message type'''
        mapping.register_message(msg)


class TextUIMixin(object):
    # This class demonstrates easy test-based UI
    # integration between the device and wallet.
    # You can implement similar functionality
    # by implementing your own GuiMixin with
    # graphical widgets for every type of these callbacks.

    def __init__(self, *args, **kwargs):
        super(TextUIMixin, self).__init__(*args, **kwargs)

    @staticmethod
    def print(text):
        print(text, file=sys.stderr)

    def callback_ButtonRequest(self, msg):
        # log("Sending ButtonAck for %s " % get_buttonrequest_value(msg.code))
        return proto.ButtonAck()

    def callback_RecoveryMatrix(self, msg):
        if self.recovery_matrix_first_pass:
            self.recovery_matrix_first_pass = False
            self.print("Use the numeric keypad to describe positions.  For the word list use only left and right keys.")
            self.print("Use backspace to correct an entry.  The keypad layout is:")
            self.print("    7 8 9     7 | 9")
            self.print("    4 5 6     4 | 6")
            self.print("    1 2 3     1 | 3")
        while True:
            character = getch()
            if character in ('\x03', '\x04'):
                return proto.Cancel()

            if character in ('\x08', '\x7f'):
                return proto.WordAck(word='\x08')

            # ignore middle column if only 6 keys requested.
            if msg.type == proto.WordRequestType.Matrix6 and character in ('2', '5', '8'):
                continue

            if character.isdigit():
                return proto.WordAck(word=character)

    def callback_PinMatrixRequest(self, msg):
        if msg.type == proto.PinMatrixRequestType.Current:
            desc = 'current PIN'
        elif msg.type == proto.PinMatrixRequestType.NewFirst:
            desc = 'new PIN'
        elif msg.type == proto.PinMatrixRequestType.NewSecond:
            desc = 'new PIN again'
        else:
            desc = 'PIN'

        self.print("Use the numeric keypad to describe number positions. The layout is:")
        self.print("    7 8 9")
        self.print("    4 5 6")
        self.print("    1 2 3")
        self.print("Please enter %s: " % desc)
        pin = getpass.getpass('')
        if not pin.isdigit():
            raise ValueError('Non-numerical PIN provided')
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        if msg.on_device is True:
            return proto.PassphraseAck()

        if os.getenv("PASSPHRASE") is not None:
            self.print("Passphrase required. Using PASSPHRASE environment variable.")
            passphrase = Mnemonic.normalize_string(os.getenv("PASSPHRASE"))
            return proto.PassphraseAck(passphrase=passphrase)

        self.print("Passphrase required: ")
        passphrase = getpass.getpass('')
        self.print("Confirm your Passphrase: ")
        if passphrase == getpass.getpass(''):
            passphrase = Mnemonic.normalize_string(passphrase)
            return proto.PassphraseAck(passphrase=passphrase)
        else:
            self.print("Passphrase did not match! ")
            exit()

    def callback_PassphraseStateRequest(self, msg):
        return proto.PassphraseStateAck()

    def callback_WordRequest(self, msg):
        if msg.type in (proto.WordRequestType.Matrix9,
                        proto.WordRequestType.Matrix6):
            return self.callback_RecoveryMatrix(msg)
        self.print("Enter one word of mnemonic: ")
        word = input()
        if self.expand:
            word = self.mnemonic_wordlist.expand_word(word)
        return proto.WordAck(word=word)


class DebugLinkMixin(object):
    # This class implements automatic responses
    # and other functionality for unit tests
    # for various callbacks, created in order
    # to automatically pass unit tests.
    #
    # This mixing should be used only for purposes
    # of unit testing, because it will fail to work
    # without special DebugLink interface provided
    # by the device.
    DEBUG = LOG.getChild('debug_link').debug

    def __init__(self, *args, **kwargs):
        super(DebugLinkMixin, self).__init__(*args, **kwargs)
        self.debug = None
        self.in_with_statement = 0
        self.button_wait = 0
        self.screenshot_id = 0

        # Always press Yes and provide correct pin
        self.setup_debuglink(True, True)

        # Do not expect any specific response from device
        self.expected_responses = None

        # Use blank passphrase
        self.set_passphrase('')

    def close(self):
        super(DebugLinkMixin, self).close()
        if self.debug:
            self.debug.close()

    def set_debuglink(self, debug_transport):
        self.debug = DebugLink(debug_transport)

    def set_buttonwait(self, secs):
        self.button_wait = secs

    def __enter__(self):
        # For usage in with/expected_responses
        self.in_with_statement += 1
        return self

    def __exit__(self, _type, value, traceback):
        self.in_with_statement -= 1

        if _type is not None:
            # Another exception raised
            return False

        # return isinstance(value, TypeError)
        # Evaluate missed responses in 'with' statement
        if self.expected_responses is not None and len(self.expected_responses):
            raise RuntimeError("Some of expected responses didn't come from device: %s" %
                               [repr(x) for x in self.expected_responses])

        # Cleanup
        self.expected_responses = None
        return False

    def set_expected_responses(self, expected):
        if not self.in_with_statement:
            raise RuntimeError("Must be called inside 'with' statement")
        self.expected_responses = expected

    def setup_debuglink(self, button, pin_correct):
        self.button = button  # True -> YES button, False -> NO button
        self.pin_correct = pin_correct

    def set_passphrase(self, passphrase):
        self.passphrase = Mnemonic.normalize_string(passphrase)

    def set_mnemonic(self, mnemonic):
        self.mnemonic = Mnemonic.normalize_string(mnemonic).split(' ')

    def call_raw(self, msg):
        __tracebackhide__ = True  # pytest traceback hiding - this function won't appear in tracebacks

        if SCREENSHOT and self.debug:
            from PIL import Image
            layout = self.debug.read_layout()
            im = Image.new("RGB", (128, 64))
            pix = im.load()
            for x in range(128):
                for y in range(64):
                    rx, ry = 127 - x, 63 - y
                    if (ord(layout[rx + (ry / 8) * 128]) & (1 << (ry % 8))) > 0:
                        pix[x, y] = (255, 255, 255)
            im.save('scr%05d.png' % self.screenshot_id)
            self.screenshot_id += 1

        resp = super(DebugLinkMixin, self).call_raw(msg)
        self._check_request(resp)
        return resp

    def _check_request(self, msg):
        __tracebackhide__ = True  # pytest traceback hiding - this function won't appear in tracebacks

        if self.expected_responses is not None:
            try:
                expected = self.expected_responses.pop(0)
            except IndexError:
                raise AssertionError(proto.FailureType.UnexpectedMessage,
                                     "Got %s, but no message has been expected" % repr(msg))

            if msg.__class__ != expected.__class__:
                raise AssertionError(proto.FailureType.UnexpectedMessage,
                                     "Expected %s, got %s" % (repr(expected), repr(msg)))

            for field, value in expected.__dict__.items():
                if value is None or value == []:
                    continue
                if getattr(msg, field) != value:
                    raise AssertionError(proto.FailureType.UnexpectedMessage,
                                         "Expected %s, got %s" % (repr(expected), repr(msg)))

    def callback_ButtonRequest(self, msg):
        self.DEBUG("ButtonRequest code: " + get_buttonrequest_value(msg.code))

        self.DEBUG("Pressing button " + str(self.button))
        if self.button_wait:
            self.DEBUG("Waiting %d seconds " % self.button_wait)
            time.sleep(self.button_wait)
        self.debug.press_button(self.button)
        return proto.ButtonAck()

    def callback_PinMatrixRequest(self, msg):
        if self.pin_correct:
            pin = self.debug.read_pin_encoded()
        else:
            pin = '444222'
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        self.DEBUG("Provided passphrase: '%s'" % self.passphrase)
        return proto.PassphraseAck(passphrase=self.passphrase)

    def callback_PassphraseStateRequest(self, msg):
        return proto.PassphraseStateAck()

    def callback_WordRequest(self, msg):
        (word, pos) = self.debug.read_recovery_word()
        if word != '':
            return proto.WordAck(word=word)
        if pos != 0:
            return proto.WordAck(word=self.mnemonic[pos - 1])

        raise RuntimeError("Unexpected call")


class ProtocolMixin(object):
    VENDORS = ('bitcointrezor.com', 'trezor.io')

    def __init__(self, state=None, *args, **kwargs):
        super(ProtocolMixin, self).__init__(*args, **kwargs)
        self.state = state
        self.init_device()
        self.tx_api = None

    def set_tx_api(self, tx_api):
        self.tx_api = tx_api

    def init_device(self):
        init_msg = proto.Initialize()
        if self.state is not None:
            init_msg.state = self.state
        self.features = expect(proto.Features)(self.call)(init_msg)
        if str(self.features.vendor) not in self.VENDORS:
            raise RuntimeError("Unsupported device")

    def _get_local_entropy(self):
        return os.urandom(32)

    @staticmethod
    def _convert_prime(n: tools.Address) -> tools.Address:
        # Convert minus signs to uint32 with flag
        return [tools.H_(int(abs(x))) if x < 0 else x for x in n]

    @staticmethod
    def expand_path(n):
        warnings.warn('expand_path is deprecated, use tools.parse_path', DeprecationWarning)
        return tools.parse_path(n)

    @expect(proto.PublicKey)
    def get_public_node(self, n, ecdsa_curve_name=None, show_display=False, coin_name=None):
        n = self._convert_prime(n)
        return self.call(proto.GetPublicKey(address_n=n, ecdsa_curve_name=ecdsa_curve_name, show_display=show_display, coin_name=coin_name))

    @field('address')
    @expect(proto.Address)
    def get_address(self, coin_name, n, show_display=False, multisig=None, script_type=proto.InputScriptType.SPENDADDRESS):
        n = self._convert_prime(n)
        if multisig:
            return self.call(proto.GetAddress(address_n=n, coin_name=coin_name, show_display=show_display, multisig=multisig, script_type=script_type))
        else:
            return self.call(proto.GetAddress(address_n=n, coin_name=coin_name, show_display=show_display, script_type=script_type))

    @field('address')
    @expect(proto.EthereumAddress)
    def ethereum_get_address(self, n, show_display=False, multisig=None):
        n = self._convert_prime(n)
        return self.call(proto.EthereumGetAddress(address_n=n, show_display=show_display))

    @session
    def ethereum_sign_tx(self, n, nonce, gas_price, gas_limit, to, value, data=None, chain_id=None, tx_type=None):
        def int_to_big_endian(value):
            return value.to_bytes((value.bit_length() + 7) // 8, 'big')

        n = self._convert_prime(n)

        msg = proto.EthereumSignTx(
            address_n=n,
            nonce=int_to_big_endian(nonce),
            gas_price=int_to_big_endian(gas_price),
            gas_limit=int_to_big_endian(gas_limit),
            value=int_to_big_endian(value))

        if to:
            msg.to = to

        if data:
            msg.data_length = len(data)
            data, chunk = data[1024:], data[:1024]
            msg.data_initial_chunk = chunk

        if chain_id:
            msg.chain_id = chain_id

        if tx_type is not None:
            msg.tx_type = tx_type

        response = self.call(msg)

        while response.data_length is not None:
            data_length = response.data_length
            data, chunk = data[data_length:], data[:data_length]
            response = self.call(proto.EthereumTxAck(data_chunk=chunk))

        return response.signature_v, response.signature_r, response.signature_s

    @expect(proto.EthereumMessageSignature)
    def ethereum_sign_message(self, n, message):
        n = self._convert_prime(n)
        message = normalize_nfc(message)
        return self.call(proto.EthereumSignMessage(address_n=n, message=message))

    def ethereum_verify_message(self, address, signature, message):
        message = normalize_nfc(message)
        try:
            resp = self.call(proto.EthereumVerifyMessage(address=address, signature=signature, message=message))
        except CallException as e:
            resp = e
        if isinstance(resp, proto.Success):
            return True
        return False

    #
    # Lisk functions
    #

    @field('address')
    @expect(proto.LiskAddress)
    def lisk_get_address(self, n, show_display=False):
        n = self._convert_prime(n)
        return self.call(proto.LiskGetAddress(address_n=n, show_display=show_display))

    @expect(proto.LiskPublicKey)
    def lisk_get_public_key(self, n, show_display=False):
        n = self._convert_prime(n)
        return self.call(proto.LiskGetPublicKey(address_n=n, show_display=show_display))

    @expect(proto.LiskMessageSignature)
    def lisk_sign_message(self, n, message):
        n = self._convert_prime(n)
        message = normalize_nfc(message)
        return self.call(proto.LiskSignMessage(address_n=n, message=message))

    def lisk_verify_message(self, pubkey, signature, message):
        message = normalize_nfc(message)
        try:
            resp = self.call(proto.LiskVerifyMessage(signature=signature, public_key=pubkey, message=message))
        except CallException as e:
            resp = e
        return isinstance(resp, proto.Success)

    @expect(proto.LiskSignedTx)
    def lisk_sign_tx(self, n, transaction):
        n = self._convert_prime(n)

        def asset_to_proto(asset):
            msg = proto.LiskTransactionAsset()

            if "votes" in asset:
                msg.votes = asset["votes"]
            if "data" in asset:
                msg.data = asset["data"]
            if "signature" in asset:
                msg.signature = proto.LiskSignatureType()
                msg.signature.public_key = binascii.unhexlify(asset["signature"]["publicKey"])
            if "delegate" in asset:
                msg.delegate = proto.LiskDelegateType()
                msg.delegate.username = asset["delegate"]["username"]
            if "multisignature" in asset:
                msg.multisignature = proto.LiskMultisignatureType()
                msg.multisignature.min = asset["multisignature"]["min"]
                msg.multisignature.life_time = asset["multisignature"]["lifetime"]
                msg.multisignature.keys_group = asset["multisignature"]["keysgroup"]
            return msg

        msg = proto.LiskTransactionCommon()

        msg.type = transaction["type"]
        msg.fee = int(transaction["fee"])  # Lisk use strings for big numbers (javascript issue)
        msg.amount = int(transaction["amount"])  # And we convert it back to number
        msg.timestamp = transaction["timestamp"]

        if "recipientId" in transaction:
            msg.recipient_id = transaction["recipientId"]
        if "senderPublicKey" in transaction:
            msg.sender_public_key = binascii.unhexlify(transaction["senderPublicKey"])
        if "requesterPublicKey" in transaction:
            msg.requester_public_key = binascii.unhexlify(transaction["requesterPublicKey"])
        if "signature" in transaction:
            msg.signature = binascii.unhexlify(transaction["signature"])

        msg.asset = asset_to_proto(transaction["asset"])
        return self.call(proto.LiskSignTx(address_n=n, transaction=msg))

    @field('entropy')
    @expect(proto.Entropy)
    def get_entropy(self, size):
        return self.call(proto.GetEntropy(size=size))

    @field('message')
    @expect(proto.Success)
    def ping(self, msg, button_protection=False, pin_protection=False, passphrase_protection=False):
        msg = proto.Ping(message=msg,
                         button_protection=button_protection,
                         pin_protection=pin_protection,
                         passphrase_protection=passphrase_protection)
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @field('message')
    @expect(proto.Success)
    def apply_settings(self, label=None, language=None, use_passphrase=None, homescreen=None, passphrase_source=None, auto_lock_delay_ms=None):
        settings = proto.ApplySettings()
        if label is not None:
            settings.label = label
        if language:
            settings.language = language
        if use_passphrase is not None:
            settings.use_passphrase = use_passphrase
        if homescreen is not None:
            settings.homescreen = homescreen
        if passphrase_source is not None:
            settings.passphrase_source = passphrase_source
        if auto_lock_delay_ms is not None:
            settings.auto_lock_delay_ms = auto_lock_delay_ms

        out = self.call(settings)
        self.init_device()  # Reload Features
        return out

    @field('message')
    @expect(proto.Success)
    def apply_flags(self, flags):
        out = self.call(proto.ApplyFlags(flags=flags))
        self.init_device()  # Reload Features
        return out

    @field('message')
    @expect(proto.Success)
    def clear_session(self):
        return self.call(proto.ClearSession())

    @field('message')
    @expect(proto.Success)
    def change_pin(self, remove=False):
        ret = self.call(proto.ChangePin(remove=remove))
        self.init_device()  # Re-read features
        return ret

    @expect(proto.MessageSignature)
    def sign_message(self, coin_name, n, message, script_type=proto.InputScriptType.SPENDADDRESS):
        n = self._convert_prime(n)
        message = normalize_nfc(message)
        return self.call(proto.SignMessage(coin_name=coin_name, address_n=n, message=message, script_type=script_type))

    @expect(proto.SignedIdentity)
    def sign_identity(self, identity, challenge_hidden, challenge_visual, ecdsa_curve_name=None):
        return self.call(proto.SignIdentity(identity=identity, challenge_hidden=challenge_hidden, challenge_visual=challenge_visual, ecdsa_curve_name=ecdsa_curve_name))

    @expect(proto.ECDHSessionKey)
    def get_ecdh_session_key(self, identity, peer_public_key, ecdsa_curve_name=None):
        return self.call(proto.GetECDHSessionKey(identity=identity, peer_public_key=peer_public_key, ecdsa_curve_name=ecdsa_curve_name))

    @expect(proto.CosiCommitment)
    def cosi_commit(self, n, data):
        n = self._convert_prime(n)
        return self.call(proto.CosiCommit(address_n=n, data=data))

    @expect(proto.CosiSignature)
    def cosi_sign(self, n, data, global_commitment, global_pubkey):
        n = self._convert_prime(n)
        return self.call(proto.CosiSign(address_n=n, data=data, global_commitment=global_commitment, global_pubkey=global_pubkey))

    @field('message')
    @expect(proto.Success)
    def set_u2f_counter(self, u2f_counter):
        ret = self.call(proto.SetU2FCounter(u2f_counter=u2f_counter))
        return ret

    @field("address")
    @expect(proto.NEMAddress)
    def nem_get_address(self, n, network, show_display=False):
        n = self._convert_prime(n)
        return self.call(proto.NEMGetAddress(address_n=n, network=network, show_display=show_display))

    @expect(proto.NEMSignedTx)
    def nem_sign_tx(self, n, transaction):
        n = self._convert_prime(n)
        try:
            msg = nem.create_sign_tx(transaction)
        except ValueError as e:
            raise CallException(e.message)

        assert msg.transaction is not None
        msg.transaction.address_n = n
        return self.call(msg)

    def verify_message(self, coin_name, address, signature, message):
        message = normalize_nfc(message)
        try:
            resp = self.call(proto.VerifyMessage(address=address, signature=signature, message=message, coin_name=coin_name))
        except CallException as e:
            resp = e
        if isinstance(resp, proto.Success):
            return True
        return False

    @expect(proto.EncryptedMessage)
    def encrypt_message(self, pubkey, message, display_only, coin_name, n):
        if coin_name and n:
            n = self._convert_prime(n)
            return self.call(proto.EncryptMessage(pubkey=pubkey, message=message, display_only=display_only, coin_name=coin_name, address_n=n))
        else:
            return self.call(proto.EncryptMessage(pubkey=pubkey, message=message, display_only=display_only))

    @expect(proto.DecryptedMessage)
    def decrypt_message(self, n, nonce, message, msg_hmac):
        n = self._convert_prime(n)
        return self.call(proto.DecryptMessage(address_n=n, nonce=nonce, message=message, hmac=msg_hmac))

    @field('value')
    @expect(proto.CipheredKeyValue)
    def encrypt_keyvalue(self, n, key, value, ask_on_encrypt=True, ask_on_decrypt=True, iv=b''):
        n = self._convert_prime(n)
        return self.call(proto.CipherKeyValue(address_n=n,
                                              key=key,
                                              value=value,
                                              encrypt=True,
                                              ask_on_encrypt=ask_on_encrypt,
                                              ask_on_decrypt=ask_on_decrypt,
                                              iv=iv))

    @field('value')
    @expect(proto.CipheredKeyValue)
    def decrypt_keyvalue(self, n, key, value, ask_on_encrypt=True, ask_on_decrypt=True, iv=b''):
        n = self._convert_prime(n)
        return self.call(proto.CipherKeyValue(address_n=n,
                                              key=key,
                                              value=value,
                                              encrypt=False,
                                              ask_on_encrypt=ask_on_encrypt,
                                              ask_on_decrypt=ask_on_decrypt,
                                              iv=iv))

    def _prepare_sign_tx(self, inputs, outputs):
        tx = proto.TransactionType()
        tx.inputs = inputs
        tx.outputs = outputs

        txes = {None: tx}

        for inp in inputs:
            if inp.prev_hash in txes:
                continue

            if inp.script_type in (proto.InputScriptType.SPENDP2SHWITNESS,
                                   proto.InputScriptType.SPENDWITNESS):
                continue

            if not self.tx_api:
                raise RuntimeError('TX_API not defined')

            prev_tx = self.tx_api.get_tx(binascii.hexlify(inp.prev_hash).decode('utf-8'))
            txes[inp.prev_hash] = prev_tx

        return txes

    @session
    def sign_tx(self, coin_name, inputs, outputs, version=None, lock_time=None, expiry=None, overwintered=None, debug_processor=None):

        # start = time.time()
        txes = self._prepare_sign_tx(inputs, outputs)

        # Prepare and send initial message
        tx = proto.SignTx()
        tx.inputs_count = len(inputs)
        tx.outputs_count = len(outputs)
        tx.coin_name = coin_name
        if version is not None:
            tx.version = version
        if lock_time is not None:
            tx.lock_time = lock_time
        if expiry is not None:
            tx.expiry = expiry
        if overwintered is not None:
            tx.overwintered = overwintered
        res = self.call(tx)

        # Prepare structure for signatures
        signatures = [None] * len(inputs)
        serialized_tx = b''

        counter = 0
        while True:
            counter += 1

            if isinstance(res, proto.Failure):
                raise CallException("Signing failed")

            if not isinstance(res, proto.TxRequest):
                raise CallException("Unexpected message")

            # If there's some part of signed transaction, let's add it
            if res.serialized and res.serialized.serialized_tx:
                # log("RECEIVED PART OF SERIALIZED TX (%d BYTES)" % len(res.serialized.serialized_tx))
                serialized_tx += res.serialized.serialized_tx

            if res.serialized and res.serialized.signature_index is not None:
                if signatures[res.serialized.signature_index] is not None:
                    raise ValueError("Signature for index %d already filled" % res.serialized.signature_index)
                signatures[res.serialized.signature_index] = res.serialized.signature

            if res.request_type == proto.RequestType.TXFINISHED:
                # Device didn't ask for more information, finish workflow
                break

            # Device asked for one more information, let's process it.
            if not res.details.tx_hash:
                current_tx = txes[None]
            else:
                current_tx = txes[bytes(res.details.tx_hash)]

            if res.request_type == proto.RequestType.TXMETA:
                msg = proto.TransactionType()
                msg.version = current_tx.version
                msg.lock_time = current_tx.lock_time
                msg.inputs_cnt = len(current_tx.inputs)
                if res.details.tx_hash:
                    msg.outputs_cnt = len(current_tx.bin_outputs)
                else:
                    msg.outputs_cnt = len(current_tx.outputs)
                msg.extra_data_len = len(current_tx.extra_data) if current_tx.extra_data else 0
                res = self.call(proto.TxAck(tx=msg))
                continue

            elif res.request_type == proto.RequestType.TXINPUT:
                msg = proto.TransactionType()
                msg.inputs = [current_tx.inputs[res.details.request_index]]
                if debug_processor is not None:
                    # msg needs to be deep copied so when it's modified
                    # the other messages stay intact
                    from copy import deepcopy
                    msg = deepcopy(msg)
                    # If debug_processor function is provided,
                    # pass thru it the request and prepared response.
                    # This is useful for tests, see test_msg_signtx
                    msg = debug_processor(res, msg)

                res = self.call(proto.TxAck(tx=msg))
                continue

            elif res.request_type == proto.RequestType.TXOUTPUT:
                msg = proto.TransactionType()
                if res.details.tx_hash:
                    msg.bin_outputs = [current_tx.bin_outputs[res.details.request_index]]
                else:
                    msg.outputs = [current_tx.outputs[res.details.request_index]]

                if debug_processor is not None:
                    # msg needs to be deep copied so when it's modified
                    # the other messages stay intact
                    from copy import deepcopy
                    msg = deepcopy(msg)
                    # If debug_processor function is provided,
                    # pass thru it the request and prepared response.
                    # This is useful for tests, see test_msg_signtx
                    msg = debug_processor(res, msg)

                res = self.call(proto.TxAck(tx=msg))
                continue

            elif res.request_type == proto.RequestType.TXEXTRADATA:
                o, l = res.details.extra_data_offset, res.details.extra_data_len
                msg = proto.TransactionType()
                msg.extra_data = current_tx.extra_data[o:o + l]
                res = self.call(proto.TxAck(tx=msg))
                continue

        if None in signatures:
            raise RuntimeError("Some signatures are missing!")

        # log("SIGNED IN %.03f SECONDS, CALLED %d MESSAGES, %d BYTES" %
        #    (time.time() - start, counter, len(serialized_tx)))

        return (signatures, serialized_tx)

    @field('message')
    @expect(proto.Success)
    def wipe_device(self):
        ret = self.call(proto.WipeDevice())
        self.init_device()
        return ret

    @field('message')
    @expect(proto.Success)
    def recovery_device(self, word_count, passphrase_protection, pin_protection, label, language, type=proto.RecoveryDeviceType.ScrambledWords, expand=False, dry_run=False):
        if self.features.initialized and not dry_run:
            raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

        if word_count not in (12, 18, 24):
            raise ValueError("Invalid word count. Use 12/18/24")

        self.recovery_matrix_first_pass = True

        self.expand = expand
        if self.expand:
            # optimization to load the wordlist once, instead of for each recovery word
            self.mnemonic_wordlist = Mnemonic('english')

        res = self.call(proto.RecoveryDevice(
            word_count=int(word_count),
            passphrase_protection=bool(passphrase_protection),
            pin_protection=bool(pin_protection),
            label=label,
            language=language,
            enforce_wordlist=True,
            type=type,
            dry_run=dry_run))

        self.init_device()
        return res

    @field('message')
    @expect(proto.Success)
    @session
    def reset_device(self, display_random, strength, passphrase_protection, pin_protection, label, language, u2f_counter=0, skip_backup=False):
        if self.features.initialized:
            raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

        # Begin with device reset workflow
        msg = proto.ResetDevice(display_random=display_random,
                                strength=strength,
                                passphrase_protection=bool(passphrase_protection),
                                pin_protection=bool(pin_protection),
                                language=language,
                                label=label,
                                u2f_counter=u2f_counter,
                                skip_backup=bool(skip_backup))

        resp = self.call(msg)
        if not isinstance(resp, proto.EntropyRequest):
            raise RuntimeError("Invalid response, expected EntropyRequest")

        external_entropy = self._get_local_entropy()
        LOG.debug("Computer generated entropy: " + binascii.hexlify(external_entropy).decode())
        ret = self.call(proto.EntropyAck(entropy=external_entropy))
        self.init_device()
        return ret

    @field('message')
    @expect(proto.Success)
    def backup_device(self):
        ret = self.call(proto.BackupDevice())
        return ret

    @field('message')
    @expect(proto.Success)
    def load_device_by_mnemonic(self, mnemonic, pin, passphrase_protection, label, language='english', skip_checksum=False, expand=False):
        # Convert mnemonic to UTF8 NKFD
        mnemonic = Mnemonic.normalize_string(mnemonic)

        # Convert mnemonic to ASCII stream
        mnemonic = mnemonic.encode('utf-8')

        m = Mnemonic('english')

        if expand:
            mnemonic = m.expand(mnemonic)

        if not skip_checksum and not m.check(mnemonic):
            raise ValueError("Invalid mnemonic checksum")

        if self.features.initialized:
            raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

        resp = self.call(proto.LoadDevice(mnemonic=mnemonic, pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language=language,
                                          label=label,
                                          skip_checksum=skip_checksum))
        self.init_device()
        return resp

    @field('message')
    @expect(proto.Success)
    def load_device_by_xprv(self, xprv, pin, passphrase_protection, label, language):
        if self.features.initialized:
            raise RuntimeError("Device is initialized already. Call wipe_device() and try again.")

        if xprv[0:4] not in ('xprv', 'tprv'):
            raise ValueError("Unknown type of xprv")

        if not 100 < len(xprv) < 112:  # yes this is correct in Python
            raise ValueError("Invalid length of xprv")

        node = proto.HDNodeType()
        data = binascii.hexlify(tools.b58decode(xprv, None))

        if data[90:92] != b'00':
            raise ValueError("Contain invalid private key")

        checksum = binascii.hexlify(tools.btc_hash(binascii.unhexlify(data[:156]))[:4])
        if checksum != data[156:]:
            raise ValueError("Checksum doesn't match")

        # version 0488ade4
        # depth 00
        # fingerprint 00000000
        # child_num 00000000
        # chaincode 873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508
        # privkey   00e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35
        # checksum e77e9d71

        node.depth = int(data[8:10], 16)
        node.fingerprint = int(data[10:18], 16)
        node.child_num = int(data[18:26], 16)
        node.chain_code = binascii.unhexlify(data[26:90])
        node.private_key = binascii.unhexlify(data[92:156])  # skip 0x00 indicating privkey

        resp = self.call(proto.LoadDevice(node=node,
                                          pin=pin,
                                          passphrase_protection=passphrase_protection,
                                          language=language,
                                          label=label))
        self.init_device()
        return resp

    @session
    def firmware_update(self, fp):
        if self.features.bootloader_mode is False:
            raise RuntimeError("Device must be in bootloader mode")

        data = fp.read()

        resp = self.call(proto.FirmwareErase(length=len(data)))
        if isinstance(resp, proto.Failure) and resp.code == proto.FailureType.FirmwareError:
            return False

        # TREZORv1 method
        if isinstance(resp, proto.Success):
            fingerprint = hashlib.sha256(data[256:]).hexdigest()
            LOG.debug("Firmware fingerprint: " + fingerprint)
            resp = self.call(proto.FirmwareUpload(payload=data))
            if isinstance(resp, proto.Success):
                return True
            elif isinstance(resp, proto.Failure) and resp.code == proto.FailureType.FirmwareError:
                return False
            raise RuntimeError("Unexpected result %s" % resp)

        # TREZORv2 method
        if isinstance(resp, proto.FirmwareRequest):
            import pyblake2
            while True:
                payload = data[resp.offset:resp.offset + resp.length]
                digest = pyblake2.blake2s(payload).digest()
                resp = self.call(proto.FirmwareUpload(payload=payload, hash=digest))
                if isinstance(resp, proto.FirmwareRequest):
                    continue
                elif isinstance(resp, proto.Success):
                    return True
                elif isinstance(resp, proto.Failure) and resp.code == proto.FailureType.FirmwareError:
                    return False
                raise RuntimeError("Unexpected result %s" % resp)

        raise RuntimeError("Unexpected message %s" % resp)

    @field('message')
    @expect(proto.Success)
    def self_test(self):
        if self.features.bootloader_mode is False:
            raise RuntimeError("Device must be in bootloader mode")

        return self.call(proto.SelfTest(payload=b'\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC'))

    @expect(proto.StellarPublicKey)
    def stellar_get_public_key(self, address_n):
        return self.call(proto.StellarGetPublicKey(address_n=address_n))

    def stellar_sign_transaction(self, tx, operations, address_n, network_passphrase=None):
        # default networkPassphrase to the public network
        if network_passphrase is None:
            network_passphrase = "Public Global Stellar Network ; September 2015"

        tx.network_passphrase = network_passphrase
        tx.address_n = address_n
        tx.num_operations = len(operations)
        # Signing loop works as follows:
        #
        # 1. Start with tx (header information for the transaction) and operations (an array of operation protobuf messagess)
        # 2. Send the tx header to the device
        # 3. Receive a StellarTxOpRequest message
        # 4. Send operations one by one until all operations have been sent. If there are more operations to sign, the device will send a StellarTxOpRequest message
        # 5. The final message received will be StellarSignedTx which is returned from this method
        resp = self.call(tx)
        try:
            while isinstance(resp, proto.StellarTxOpRequest):
                resp = self.call(operations.pop(0))
        except IndexError:
            # pop from empty list
            raise CallException("Stellar.UnexpectedEndOfOperations",
                                "Reached end of operations without a signature.") from None

        if not isinstance(resp, proto.StellarSignedTx):
            raise CallException(proto.FailureType.UnexpectedMessage, resp)

        if operations:
            raise CallException("Stellar.UnprocessedOperations",
                                "Received a signature before processing all operations.")

        return resp


class TrezorClient(ProtocolMixin, TextUIMixin, BaseClient):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(transport=transport, *args, **kwargs)


class TrezorClientDebugLink(ProtocolMixin, DebugLinkMixin, BaseClient):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(transport=transport, *args, **kwargs)
