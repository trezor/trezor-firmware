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

from trezorlib import lisk

VECTORS = (  # pubkey, signature, message
    (
        "eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294",
        "7858ae7cd52ea6d4b17e800ca60144423db5560bfd618b663ffbf26ab66758563df45cbffae8463db22dc285dd94309083b8c807776085b97d05374d79867d05",
        "This is an example of a signed message.",
    ),
    (
        "8bca6b65a1a877767b746ea0b3c4310d404aa113df99c1b554e1802d70185ab5",
        "458ca5896d0934866992268f7509b5e954d568b1251e20c19bd3149ee3c86ffb5a44d1c2a0abbb99a3ab4767272dbb0e419b4579e890a24919ebbbe6cc0f970f",
        "VeryLongMessage!" * 64,
    ),
)


@pytest.mark.altcoin
@pytest.mark.lisk
@pytest.mark.parametrize("pubkey, signature, message", VECTORS)
def test_verify(client, pubkey, signature, message):
    with client:
        lisk.verify_message(
            client, bytes.fromhex(pubkey), bytes.fromhex(signature), message
        )
