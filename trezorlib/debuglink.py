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

from mnemonic import Mnemonic

from . import messages as proto, tools
from .tools import expect


def pin_info(pin):
    print("Device asks for PIN %s" % pin)


def button_press(yes_no):
    print("User pressed", '"y"' if yes_no else '"n"')


class DebugLink(object):
    def __init__(self, transport, pin_func=pin_info, button_func=button_press):
        self.transport = transport
        self.transport.session_begin()

        self.pin_func = pin_func
        self.button_func = button_func

    def close(self):
        self.transport.session_end()

    def _call(self, msg, nowait=False):
        self.transport.write(msg)
        if nowait:
            return None
        ret = self.transport.read()
        return ret

    def read_pin(self):
        obj = self._call(proto.DebugLinkGetState())
        print("Read PIN:", obj.pin)
        print("Read matrix:", obj.matrix)

        return (obj.pin, obj.matrix)

    def read_pin_encoded(self):
        pin, _ = self.read_pin()
        pin_encoded = self.encode_pin(pin)
        self.pin_func(pin_encoded)
        return pin_encoded

    def encode_pin(self, pin):
        _, matrix = self.read_pin()

        # Now we have real PIN and PIN matrix.
        # We have to encode that into encoded pin,
        # because application must send back positions
        # on keypad, not a real PIN.
        pin_encoded = "".join([str(matrix.index(p) + 1) for p in pin])

        print("Encoded PIN:", pin_encoded)
        return pin_encoded

    def read_layout(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.layout

    def read_mnemonic(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.mnemonic

    def read_node(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.node

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

    def press_button(self, yes_no):
        print("Pressing", yes_no)
        self.button_func(yes_no)
        self._call(proto.DebugLinkDecision(yes_no=yes_no), nowait=True)

    def press_yes(self):
        self.press_button(True)

    def press_no(self):
        self.press_button(False)

    def swipe(self, up_down):
        print("Swiping", up_down)
        self._call(proto.DebugLinkDecision(up_down=up_down), nowait=True)

    def swipe_up(self):
        self.swipe(True)

    def swipe_down(self):
        self.swipe(False)

    def input(self, text):
        self._call(proto.DebugLinkDecision(input=text), nowait=True)

    def stop(self):
        self._call(proto.DebugLinkStop(), nowait=True)

    def memory_read(self, address, length):
        obj = self._call(proto.DebugLinkMemoryRead(address=address, length=length))
        return obj.memory

    def memory_write(self, address, memory, flash=False):
        self._call(
            proto.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash),
            nowait=True,
        )

    def flash_erase(self, sector):
        self._call(proto.DebugLinkFlashErase(sector=sector), nowait=True)


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
            "Device is initialized already. Call wipe_device() and try again."
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
    data = binascii.hexlify(tools.b58decode(xprv, None))

    if data[90:92] != b"00":
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
