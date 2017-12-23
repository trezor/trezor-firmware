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
class TestMsgRecoverydeviceDryrun(TrezorTest):

    def recovery_loop(self, mnemonic, result):
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=False,
                                   pin_protection=False,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True,
                                   dry_run=True))

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

        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()

        ret = self.client.call_raw(proto.ButtonAck())
        assert isinstance(ret, result)

    def test_correct_notsame(self):
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = ['all'] * 12
        self.recovery_loop(mnemonic, proto.Failure)

    def test_correct_same(self):
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = self.mnemonic12.split(' ')
        self.recovery_loop(mnemonic, proto.Success)

    def test_incorrect(self):
        self.setup_mnemonic_nopin_nopassphrase()
        mnemonic = ['stick'] * 12
        self.recovery_loop(mnemonic, proto.Failure)
