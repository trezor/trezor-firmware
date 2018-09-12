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

import pytest

from trezorlib import misc

from .common import TrezorTest


class TestMsgCipherkeyvalue(TrezorTest):
    def test_encrypt(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # different ask values
        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            b"testing message!",
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res.hex() == "676faf8f13272af601776bc31bc14e8f"

        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            b"testing message!",
            ask_on_encrypt=True,
            ask_on_decrypt=False,
        )
        assert res.hex() == "5aa0fbcb9d7fa669880745479d80c622"

        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            b"testing message!",
            ask_on_encrypt=False,
            ask_on_decrypt=True,
        )
        assert res.hex() == "958d4f63269b61044aaedc900c8d6208"

        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            b"testing message!",
            ask_on_encrypt=False,
            ask_on_decrypt=False,
        )
        assert res.hex() == "e0cf0eb0425947000eb546cc3994bc6c"

        # different key
        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test2",
            b"testing message!",
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res.hex() == "de247a6aa6be77a134bb3f3f925f13af"

        # different message
        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            b"testing message! it is different",
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert (
            res.hex()
            == "676faf8f13272af601776bc31bc14e8f3ae1c88536bf18f1b44f1e4c2c4a613d"
        )

        # different path
        res = misc.encrypt_keyvalue(
            self.client,
            [0, 1, 3],
            b"test",
            b"testing message!",
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res.hex() == "b4811a9d492f5355a5186ddbfccaae7b"

    def test_decrypt(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # different ask values
        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            bytes.fromhex("676faf8f13272af601776bc31bc14e8f"),
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res == b"testing message!"

        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            bytes.fromhex("5aa0fbcb9d7fa669880745479d80c622"),
            ask_on_encrypt=True,
            ask_on_decrypt=False,
        )
        assert res == b"testing message!"

        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            bytes.fromhex("958d4f63269b61044aaedc900c8d6208"),
            ask_on_encrypt=False,
            ask_on_decrypt=True,
        )
        assert res == b"testing message!"

        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            bytes.fromhex("e0cf0eb0425947000eb546cc3994bc6c"),
            ask_on_encrypt=False,
            ask_on_decrypt=False,
        )
        assert res == b"testing message!"

        # different key
        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test2",
            bytes.fromhex("de247a6aa6be77a134bb3f3f925f13af"),
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res == b"testing message!"

        # different message
        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 2],
            b"test",
            bytes.fromhex(
                "676faf8f13272af601776bc31bc14e8f3ae1c88536bf18f1b44f1e4c2c4a613d"
            ),
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res == b"testing message! it is different"

        # different path
        res = misc.decrypt_keyvalue(
            self.client,
            [0, 1, 3],
            b"test",
            bytes.fromhex("b4811a9d492f5355a5186ddbfccaae7b"),
            ask_on_encrypt=True,
            ask_on_decrypt=True,
        )
        assert res == b"testing message!"

    def test_encrypt_badlen(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with pytest.raises(Exception):
            misc.encrypt_keyvalue(self.client, [0, 1, 2], b"test", b"testing")

    def test_decrypt_badlen(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with pytest.raises(Exception):
            misc.decrypt_keyvalue(self.client, [0, 1, 2], b"test", b"testing")
