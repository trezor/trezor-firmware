# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import pytest

from trezorlib import messages as proto

from .common import MNEMONIC12


@pytest.mark.skip_t2
class TestMsgRecoverydeviceDryrun:
    def recovery_loop(self, client, mnemonic, result):
        ret = client.call_raw(
            proto.RecoveryDevice(
                word_count=12,
                passphrase_protection=False,
                pin_protection=False,
                label="label",
                language="english",
                enforce_wordlist=True,
                dry_run=True,
            )
        )

        fakes = 0
        for _ in range(int(12 * 2)):
            assert isinstance(ret, proto.WordRequest)
            (word, pos) = client.debug.read_recovery_word()

            if pos != 0:
                ret = client.call_raw(proto.WordAck(word=mnemonic[pos - 1]))
                mnemonic[pos - 1] = None
            else:
                ret = client.call_raw(proto.WordAck(word=word))
                fakes += 1

            print(mnemonic)

        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()

        ret = client.call_raw(proto.ButtonAck())
        assert isinstance(ret, result)

    def test_correct_notsame(self, client):
        mnemonic = MNEMONIC12.split(" ")
        self.recovery_loop(client, mnemonic, proto.Failure)

    def test_correct_same(self, client):
        mnemonic = ["all"] * 12
        self.recovery_loop(client, mnemonic, proto.Success)

    def test_incorrect(self, client):
        mnemonic = ["stick"] * 12
        self.recovery_loop(client, mnemonic, proto.Failure)
