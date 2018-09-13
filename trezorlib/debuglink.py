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


from mnemonic import Mnemonic

from . import messages as proto, tools
from .client import TrezorClient
from .tools import expect


class DebugLink:
    def __init__(self, transport):
        self.transport = transport
        self.transport.session_begin()

    def close(self):
        self.transport.session_end()

    def _call(self, msg, nowait=False):
        self.transport.write(msg)
        if nowait:
            return None
        ret = self.transport.read()
        return ret

    def state(self):
        return self._call(proto.DebugLinkGetState())

    def read_pin(self):
        state = self.state()
        return state.pin, state.matrix

    def read_pin_encoded(self):
        return self.encode_pin(*self.read_pin())

    def encode_pin(self, pin, matrix=None):
        """Transform correct PIN according to the displayed matrix."""
        if matrix is None:
            _, matrix = self.read_pin()
        return "".join([str(matrix.index(p) + 1) for p in pin])

    def read_layout(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.layout

    def read_mnemonic(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.mnemonic

    def read_recovery_word(self):
        obj = self._call(proto.DebugLinkGetState())
        return (obj.recovery_fake_word, obj.recovery_word_pos)

    def read_reset_word(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.reset_word

    def read_reset_word_pos(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.reset_word_pos

    def read_reset_entropy(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.reset_entropy

    def read_passphrase_protection(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.passphrase_protection

    def input(self, word=None, button=None, swipe=None):
        decision = proto.DebugLinkDecision()
        if button is not None:
            decision.yes_no = button
        elif word is not None:
            decision.input = word
        elif swipe is not None:
            decision.up_down = swipe
        else:
            raise ValueError("You need to provide input data.")
        self._call(decision, nowait=True)

    def press_button(self, yes_no):
        self._call(proto.DebugLinkDecision(yes_no=yes_no), nowait=True)

    def press_yes(self):
        self.input(button=True)

    def press_no(self):
        self.input(button=False)

    def swipe_up(self):
        self.input(swipe=True)

    def swipe_down(self):
        self.input(swipe=False)

    def stop(self):
        self._call(proto.DebugLinkStop(), nowait=True)

    @expect(proto.DebugLinkMemory, field="memory")
    def memory_read(self, address, length):
        return self._call(proto.DebugLinkMemoryRead(address=address, length=length))

    def memory_write(self, address, memory, flash=False):
        self._call(
            proto.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash),
            nowait=True,
        )

    def flash_erase(self, sector):
        self._call(proto.DebugLinkFlashErase(sector=sector), nowait=True)


class DebugUI:
    def __init__(self, debuglink: DebugLink):
        self.debuglink = debuglink
        self.pin = None
        self.passphrase = "sphinx of black quartz, judge my wov"

    def button_request(self):
        self.debuglink.press_yes()

    def get_pin(self):
        if self.pin:
            return self.pin
        else:
            return self.debuglink.read_pin_encoded()

    def get_passphrase(self):
        return self.passphrase


class TrezorClientDebugLink(TrezorClient):
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

    def __init__(self, transport):
        self.debug = DebugLink(transport.find_debug())
        self.ui = DebugUI(self.debug)
        super().__init__(transport, self.ui)

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
        super().close()
        if self.debug:
            self.debug.close()

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
        # self.button = button  # True -> YES button, False -> NO button
        if pin_correct:
            self.ui.pin = None
        else:
            self.ui.pin = "444222"

    def set_passphrase(self, passphrase):
        self.ui.passphrase = Mnemonic.normalize_string(passphrase)

    def set_mnemonic(self, mnemonic):
        self.mnemonic = Mnemonic.normalize_string(mnemonic).split(" ")

    def call_raw(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        # if SCREENSHOT and self.debug:
        #     from PIL import Image

        #     layout = self.debug.state().layout
        #     im = Image.new("RGB", (128, 64))
        #     pix = im.load()
        #     for x in range(128):
        #         for y in range(64):
        #             rx, ry = 127 - x, 63 - y
        #             if (ord(layout[rx + (ry / 8) * 128]) & (1 << (ry % 8))) > 0:
        #                 pix[x, y] = (255, 255, 255)
        #     im.save("scr%05d.png" % self.screenshot_id)
        #     self.screenshot_id += 1

        resp = super().call_raw(msg)
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

    def mnemonic_callback(self, _):
        word, pos = self.debug.read_recovery_word()
        if word != "":
            return word
        if pos != 0:
            return self.mnemonic[pos - 1]

        raise RuntimeError("Unexpected call")


@expect(proto.Success, field="message")
def load_device_by_mnemonic(
    client,
    mnemonic,
    pin,
    passphrase_protection,
    label,
    language="english",
    skip_checksum=False,
    expand=False,
):
    # Convert mnemonic to UTF8 NKFD
    mnemonic = Mnemonic.normalize_string(mnemonic)

    # Convert mnemonic to ASCII stream
    mnemonic = mnemonic.encode()

    m = Mnemonic("english")

    if expand:
        mnemonic = m.expand(mnemonic)

    if not skip_checksum and not m.check(mnemonic):
        raise ValueError("Invalid mnemonic checksum")

    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call device.wipe() and try again."
        )

    resp = client.call(
        proto.LoadDevice(
            mnemonic=mnemonic,
            pin=pin,
            passphrase_protection=passphrase_protection,
            language=language,
            label=label,
            skip_checksum=skip_checksum,
        )
    )
    client.init_device()
    return resp


@expect(proto.Success, field="message")
def load_device_by_xprv(client, xprv, pin, passphrase_protection, label, language):
    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if xprv[0:4] not in ("xprv", "tprv"):
        raise ValueError("Unknown type of xprv")

    if not 100 < len(xprv) < 112:  # yes this is correct in Python
        raise ValueError("Invalid length of xprv")

    node = proto.HDNodeType()
    data = tools.b58decode(xprv, None).hex()

    if data[90:92] != "00":
        raise ValueError("Contain invalid private key")

    checksum = (tools.btc_hash(bytes.fromhex(data[:156]))[:4]).hex()
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
    node.chain_code = bytes.fromhex(data[26:90])
    node.private_key = bytes.fromhex(data[92:156])  # skip 0x00 indicating privkey

    resp = client.call(
        proto.LoadDevice(
            node=node,
            pin=pin,
            passphrase_protection=passphrase_protection,
            language=language,
            label=label,
        )
    )
    client.init_device()
    return resp


@expect(proto.Success, field="message")
def self_test(client):
    if client.features.bootloader_mode is not True:
        raise RuntimeError("Device must be in bootloader mode")

    return client.call(
        proto.SelfTest(
            payload=b"\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC"
        )
    )
