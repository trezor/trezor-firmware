# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import binascii
import functools
import getpass
import logging
import os
import sys
import time
import warnings

from mnemonic import Mnemonic

from . import (
    btc,
    cosi,
    debuglink,
    device,
    ethereum,
    firmware,
    lisk,
    mapping,
    messages as proto,
    misc,
    nem,
    stellar,
    tools,
)

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
            return key.decode()


def get_buttonrequest_value(code):
    # Converts integer code to its string representation of ButtonRequestType
    return [
        k
        for k in dir(proto.ButtonRequestType)
        if getattr(proto.ButtonRequestType, k) == code
    ][0]


class PinException(tools.CallException):
    pass


class MovedTo:
    """Deprecation redirector for methods that were formerly part of TrezorClient"""

    def __init__(self, where):
        self.where = where
        self.name = where.__module__ + "." + where.__name__

    def _deprecated_redirect(self, client, *args, **kwargs):
        """Redirector for a deprecated method on TrezorClient"""
        warnings.warn(
            "Function has been moved to %s" % self.name,
            DeprecationWarning,
            stacklevel=2,
        )
        return self.where(client, *args, **kwargs)

    def __get__(self, instance, cls):
        if instance is None:
            return self._deprecated_redirect
        else:
            return functools.partial(self._deprecated_redirect, instance)


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

    @tools.session
    def call_raw(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        self.transport.write(msg)
        return self.transport.read()

    @tools.session
    def call(self, msg):
        resp = self.call_raw(msg)
        handler_name = "callback_%s" % resp.__class__.__name__
        handler = getattr(self, handler_name, None)

        if handler is not None:
            msg = handler(resp)
            if msg is None:
                raise ValueError(
                    "Callback %s must return protobuf message, not None" % handler
                )
            resp = self.call(msg)

        return resp

    def callback_Failure(self, msg):
        if msg.code in (
            proto.FailureType.PinInvalid,
            proto.FailureType.PinCancelled,
            proto.FailureType.PinExpected,
        ):
            raise PinException(msg.code, msg.message)

        raise tools.CallException(msg.code, msg.message)

    def register_message(self, msg):
        """Allow application to register custom protobuf message type"""
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
            self.print(
                "Use the numeric keypad to describe positions.  For the word list use only left and right keys."
            )
            self.print("Use backspace to correct an entry.  The keypad layout is:")
            self.print("    7 8 9     7 | 9")
            self.print("    4 5 6     4 | 6")
            self.print("    1 2 3     1 | 3")
        while True:
            character = getch()
            if character in ("\x03", "\x04"):
                return proto.Cancel()

            if character in ("\x08", "\x7f"):
                return proto.WordAck(word="\x08")

            # ignore middle column if only 6 keys requested.
            if msg.type == proto.WordRequestType.Matrix6 and character in (
                "2",
                "5",
                "8",
            ):
                continue

            if character.isdigit():
                return proto.WordAck(word=character)

    def callback_PinMatrixRequest(self, msg):
        if msg.type == proto.PinMatrixRequestType.Current:
            desc = "current PIN"
        elif msg.type == proto.PinMatrixRequestType.NewFirst:
            desc = "new PIN"
        elif msg.type == proto.PinMatrixRequestType.NewSecond:
            desc = "new PIN again"
        else:
            desc = "PIN"

        self.print(
            "Use the numeric keypad to describe number positions. The layout is:"
        )
        self.print("    7 8 9")
        self.print("    4 5 6")
        self.print("    1 2 3")
        self.print("Please enter %s: " % desc)
        pin = getpass.getpass("")
        if not pin.isdigit():
            raise ValueError("Non-numerical PIN provided")
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        if msg.on_device is True:
            return proto.PassphraseAck()

        if os.getenv("PASSPHRASE") is not None:
            self.print("Passphrase required. Using PASSPHRASE environment variable.")
            passphrase = Mnemonic.normalize_string(os.getenv("PASSPHRASE"))
            return proto.PassphraseAck(passphrase=passphrase)

        self.print("Passphrase required: ")
        passphrase = getpass.getpass("")
        self.print("Confirm your Passphrase: ")
        if passphrase == getpass.getpass(""):
            passphrase = Mnemonic.normalize_string(passphrase)
            return proto.PassphraseAck(passphrase=passphrase)
        else:
            self.print("Passphrase did not match! ")
            exit()

    def callback_PassphraseStateRequest(self, msg):
        return proto.PassphraseStateAck()

    def callback_WordRequest(self, msg):
        if msg.type in (proto.WordRequestType.Matrix9, proto.WordRequestType.Matrix6):
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
    DEBUG = LOG.getChild("debug_link").debug

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
        self.set_passphrase("")

    def close(self):
        super(DebugLinkMixin, self).close()
        if self.debug:
            self.debug.close()

    def set_debuglink(self, debug_transport):
        self.debug = debuglink.DebugLink(debug_transport)

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
            raise RuntimeError(
                "Some of expected responses didn't come from device: %s"
                % [repr(x) for x in self.expected_responses]
            )

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
        self.mnemonic = Mnemonic.normalize_string(mnemonic).split(" ")

    def call_raw(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

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
            im.save("scr%05d.png" % self.screenshot_id)
            self.screenshot_id += 1

        resp = super(DebugLinkMixin, self).call_raw(msg)
        self._check_request(resp)
        return resp

    def _check_request(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        if self.expected_responses is not None:
            try:
                expected = self.expected_responses.pop(0)
            except IndexError:
                raise AssertionError(
                    proto.FailureType.UnexpectedMessage,
                    "Got %s, but no message has been expected" % repr(msg),
                )

            if msg.__class__ != expected.__class__:
                raise AssertionError(
                    proto.FailureType.UnexpectedMessage,
                    "Expected %s, got %s" % (repr(expected), repr(msg)),
                )

            for field, value in expected.__dict__.items():
                if value is None or value == []:
                    continue
                if getattr(msg, field) != value:
                    raise AssertionError(
                        proto.FailureType.UnexpectedMessage,
                        "Expected %s, got %s" % (repr(expected), repr(msg)),
                    )

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
            pin = "444222"
        return proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, msg):
        self.DEBUG("Provided passphrase: '%s'" % self.passphrase)
        return proto.PassphraseAck(passphrase=self.passphrase)

    def callback_PassphraseStateRequest(self, msg):
        return proto.PassphraseStateAck()

    def callback_WordRequest(self, msg):
        (word, pos) = self.debug.read_recovery_word()
        if word != "":
            return proto.WordAck(word=word)
        if pos != 0:
            return proto.WordAck(word=self.mnemonic[pos - 1])

        raise RuntimeError("Unexpected call")


class ProtocolMixin(object):
    VENDORS = ("bitcointrezor.com", "trezor.io")

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
        self.features = tools.expect(proto.Features)(self.call)(init_msg)
        if str(self.features.vendor) not in self.VENDORS:
            raise RuntimeError("Unsupported device")

    @staticmethod
    def expand_path(n):
        warnings.warn(
            "expand_path is deprecated, use tools.parse_path",
            DeprecationWarning,
            stacklevel=2,
        )
        return tools.parse_path(n)

    @tools.expect(proto.Success, field="message")
    def ping(
        self,
        msg,
        button_protection=False,
        pin_protection=False,
        passphrase_protection=False,
    ):
        msg = proto.Ping(
            message=msg,
            button_protection=button_protection,
            pin_protection=pin_protection,
            passphrase_protection=passphrase_protection,
        )
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    def _prepare_sign_tx(self, inputs, outputs):
        tx = proto.TransactionType()
        tx.inputs = inputs
        tx.outputs = outputs

        txes = {None: tx}

        for inp in inputs:
            if inp.prev_hash in txes:
                continue

            if inp.script_type in (
                proto.InputScriptType.SPENDP2SHWITNESS,
                proto.InputScriptType.SPENDWITNESS,
            ):
                continue

            if not self.tx_api:
                raise RuntimeError("TX_API not defined")

            prev_tx = self.tx_api.get_tx(binascii.hexlify(inp.prev_hash).decode())
            txes[inp.prev_hash] = prev_tx

        return txes

    @tools.expect(proto.Success, field="message")
    def clear_session(self):
        return self.call(proto.ClearSession())

    # Device functionality
    wipe_device = MovedTo(device.wipe)
    recovery_device = MovedTo(device.recover)
    reset_device = MovedTo(device.reset)
    backup_device = MovedTo(device.backup)

    # debugging
    load_device_by_mnemonic = MovedTo(debuglink.load_device_by_mnemonic)
    load_device_by_xprv = MovedTo(debuglink.load_device_by_xprv)
    self_test = MovedTo(debuglink.self_test)

    set_u2f_counter = MovedTo(device.set_u2f_counter)

    apply_settings = MovedTo(device.apply_settings)
    apply_flags = MovedTo(device.apply_flags)
    change_pin = MovedTo(device.change_pin)

    # Firmware functionality
    firmware_update = MovedTo(firmware.update)

    # BTC-like functionality
    get_public_node = MovedTo(btc.get_public_node)
    get_address = MovedTo(btc.get_address)
    sign_tx = MovedTo(btc.sign_tx)
    sign_message = MovedTo(btc.sign_message)
    verify_message = MovedTo(btc.verify_message)

    # CoSi functionality
    cosi_commit = MovedTo(cosi.commit)
    cosi_sign = MovedTo(cosi.sign)

    # Ethereum functionality
    ethereum_get_address = MovedTo(ethereum.get_address)
    ethereum_sign_tx = MovedTo(ethereum.sign_tx)
    ethereum_sign_message = MovedTo(ethereum.sign_message)
    ethereum_verify_message = MovedTo(ethereum.verify_message)

    # Lisk functionality
    lisk_get_address = MovedTo(lisk.get_address)
    lisk_get_public_key = MovedTo(lisk.get_public_key)
    lisk_sign_message = MovedTo(lisk.sign_message)
    lisk_verify_message = MovedTo(lisk.verify_message)
    lisk_sign_tx = MovedTo(lisk.sign_tx)

    # NEM functionality
    nem_get_address = MovedTo(nem.get_address)
    nem_sign_tx = MovedTo(nem.sign_tx)

    # Stellar functionality
    stellar_get_address = MovedTo(stellar.get_address)
    stellar_sign_transaction = MovedTo(stellar.sign_tx)

    # Miscellaneous cryptographic functionality
    get_entropy = MovedTo(misc.get_entropy)
    sign_identity = MovedTo(misc.sign_identity)
    get_ecdh_session_key = MovedTo(misc.get_ecdh_session_key)
    encrypt_keyvalue = MovedTo(misc.encrypt_keyvalue)
    decrypt_keyvalue = MovedTo(misc.decrypt_keyvalue)


class TrezorClient(ProtocolMixin, TextUIMixin, BaseClient):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(transport=transport, *args, **kwargs)


class TrezorClientDebugLink(ProtocolMixin, DebugLinkMixin, BaseClient):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(transport=transport, *args, **kwargs)
