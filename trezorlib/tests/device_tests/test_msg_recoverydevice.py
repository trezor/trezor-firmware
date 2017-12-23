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

from .common import *
from trezorlib import messages as proto


@pytest.mark.skip_t2
class TestMsgRecoverydevice(TrezorTest):

    def test_pin_passphrase(self):
        mnemonic = self.mnemonic12.split(' ')
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=True,
                                   pin_protection=True,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))

        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        fakes = 0
        for _ in range(int(12 * 2)):
            assert isinstance(ret, proto.WordRequest)
            (word, pos) = self.client.debug.read_recovery_word()

            if pos != 0:
                ret = self.client.call_raw(proto.WordAck(word=mnemonic[pos - 1]))
                mnemonic[pos - 1] = None
            else:
                ret = self.client.call_raw(proto.WordAck(word=word))
                fakes += 1

            print(mnemonic)

        # Workflow succesfully ended
        assert isinstance(ret, proto.Success)

        # 12 expected fake words and all words of mnemonic are used
        assert fakes == 12
        assert mnemonic == [None] * 12

        # Mnemonic is the same
        self.client.init_device()
        assert self.client.debug.read_mnemonic() == self.mnemonic12

        assert self.client.features.pin_protection is True
        assert self.client.features.passphrase_protection is True

        # Do passphrase-protected action, PassphraseRequest should be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        assert isinstance(resp, proto.PassphraseRequest)
        self.client.call_raw(proto.Cancel())

        # Do PIN-protected action, PinRequest should be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(resp, proto.PinMatrixRequest)
        self.client.call_raw(proto.Cancel())

    def test_nopin_nopassphrase(self):
        mnemonic = self.mnemonic12.split(' ')
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=False,
                                   pin_protection=False,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))

        fakes = 0
        for _ in range(int(12 * 2)):
            assert isinstance(ret, proto.WordRequest)
            (word, pos) = self.client.debug.read_recovery_word()

            if pos != 0:
                ret = self.client.call_raw(proto.WordAck(word=mnemonic[pos - 1]))
                mnemonic[pos - 1] = None
            else:
                ret = self.client.call_raw(proto.WordAck(word=word))
                fakes += 1

            print(mnemonic)

        # Workflow succesfully ended
        assert isinstance(ret, proto.Success)

        # 12 expected fake words and all words of mnemonic are used
        assert fakes == 12
        assert mnemonic == [None] * 12

        # Mnemonic is the same
        self.client.init_device()
        assert self.client.debug.read_mnemonic() == self.mnemonic12

        assert self.client.features.pin_protection is False
        assert self.client.features.passphrase_protection is False

        # Do passphrase-protected action, PassphraseRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        assert isinstance(resp, proto.Success)

        # Do PIN-protected action, PinRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        assert isinstance(resp, proto.Success)

    def test_word_fail(self):
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=False,
                                   pin_protection=False,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))

        assert isinstance(ret, proto.WordRequest)
        for _ in range(int(12 * 2)):
            (word, pos) = self.client.debug.read_recovery_word()
            if pos != 0:
                ret = self.client.call_raw(proto.WordAck(word='kwyjibo'))
                assert isinstance(ret, proto.Failure)
                break
            else:
                self.client.call_raw(proto.WordAck(word=word))

    def test_pin_fail(self):
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=True,
                                   pin_protection=True,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))

        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = self.client.debug.encode_pin(self.pin4)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        assert isinstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time, but different one
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Failure should be raised
        assert isinstance(ret, proto.Failure)

    def test_already_initialized(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with pytest.raises(Exception):
            self.client.recovery_device(12, False, False, 'label', 'english')
