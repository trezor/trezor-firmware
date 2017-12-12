# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
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

from __future__ import print_function

from . import messages as proto


def pin_info(pin):
    print("Device asks for PIN %s" % pin)


def button_press(yes_no):
    print("User pressed", '"y"' if yes_no else '"n"')


def pprint(msg):
    return "<%s> (%d bytes):\n%s" % (msg.__class__.__name__, msg.ByteSize(), msg)


class DebugLink(object):
    def __init__(self, transport, pin_func=pin_info, button_func=button_press):
        self.transport = transport
        self.transport.session_begin()

        self.pin_func = pin_func
        self.button_func = button_func

    def close(self):
        self.transport.session_end()

    def _call(self, msg, nowait=False):
        print("DEBUGLINK SEND", pprint(msg))
        self.transport.write(msg)
        if nowait:
            return
        ret = self.transport.read()
        print("DEBUGLINK RECV", pprint(ret))
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
        pin_encoded = ''.join([str(matrix.index(p) + 1) for p in pin])

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

    def stop(self):
        self._call(proto.DebugLinkStop(), nowait=True)

    def memory_read(self, address, length):
        obj = self._call(proto.DebugLinkMemoryRead(address=address, length=length))
        return obj.memory

    def memory_write(self, address, memory, flash=False):
        self._call(proto.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash), nowait=True)

    def flash_erase(self, sector):
        self._call(proto.DebugLinkFlashErase(sector=sector), nowait=True)
