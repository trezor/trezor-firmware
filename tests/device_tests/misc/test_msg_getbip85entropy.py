# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from trezorlib import messages, misc
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import (
    read_mnemonic_from_screen_bolt,
    read_mnemonic_from_screen_caesar,
    read_mnemonic_from_screen_delizia,
    read_mnemonic_from_screen_eckhart,
)

pytestmark = pytest.mark.models("core")

# Vectors computed with a reference BIP-85 implementation for the default test
# mnemonic ("all all all ...").
VECTORS = (  # path, entropy, secret
    (
        # raw entropy of an unknown application
        "m/83696968h/0h/0h",
        "e46037c5fa2d031cb2ef57c20f2816c6100acba8eca2f244b08bc01e559509ee2583ce0bf921fe23e8a9c923506e78145de05873cd804d2caa1df2c6fbe4b49f",
        None,
    ),
    (
        "m/83696968h/39h/0h/12h/0h",
        "4d9900ccb462decbe4b08d70979e7a74",
        "eternal siege creek hand combine grass name balance identify rude ozone truly",
    ),
    (
        "m/83696968h/39h/0h/18h/0h",
        "016dc805b23fed3b0d59090bb84b0938a40f854397587a7a",
        "accident hour accident good yard outside cube cancel arm seat seat image domain section atom twelve kidney start",
    ),
    (
        "m/83696968h/39h/0h/24h/0h",
        "7e6f38446ddca5dc3bdf938905c167eb4f19f5a314882ced051c3b370f76fb5b",
        "lazy keep baby sweet ski unlock urge venue math come fly story various width middle much coconut habit either island ill rocket uniform hip",
    ),
    (
        "m/83696968h/2h/0h",
        "be0dc90a097b24069b6656c60722409abb4a5c9e28cab8a56a81a147882775d1",
        "L3b9hJZQxpD4fmTmAUcrw9gTnS1otedLrGzPCHsBVDWHxpazUzdu",
    ),
    (
        "m/83696968h/32h/0h",
        "735b5ee11bb0f531ab8ab5795bc0b4a1f25835b441ba5eba38bb824aafb1cd6ecb27f25f85668cc1ed901ea3b697e48fb871cd58ef4d210414bf055e27023556",
        "xprv9s21ZrQH143K3CyDPPcZAjgRnfPDfHDpNVFYa5FPC3rW7dFsbDinihsNBfimW6FYWQDF2c8fQfUMfqqfKspn7AMoChTRQwJAG9vWDnExqNr",
    ),
    (
        "m/83696968h/128169h/64h/0h",
        "acb7bf18aaf7955053ae3f04c2aef9ef28c2e94a4e88eabaabb27da66695278d16d3e7352965aa5e1a7bfb787f0cc81b398c4b047b0acbb37d2ee418931255ec",
        None,
    ),
    (
        "m/83696968h/128169h/16h/5h",
        "9c3e718522b0dbcf5ca94758a028f92c",
        None,
    ),
    (
        "m/83696968h/707764h/21h/0h",
        "8c79c9c43977e7ecdf3eb5cd844f1d342babc91bd915b8138689d6724a12d49ccede31f14ba560ac3e84720a31684872c76ece7d3c4caf5d1b20e1769ebf9fb6",
        "jHnJxDl35+zfPrXNhE8dN",
    ),
    (
        "m/83696968h/707785h/12h/0h",
        "b0733f18722745ecea73374ac3f98fa566a8ef0202445b4bd4d84259a2c398d5a9209c5fc0d7b1ad523363307c1e6ae8e2a1d5c9e24c8e9302de4d19b72d89a9",
        "uya2cawkRX>T",
    ),
    (
        # dice rolls need SHAKE256 on the host, the device returns the raw entropy
        "m/83696968h/89101h/6h/10h/0h",
        "ee440e5e2b4e3f93dcc62400b43dc95c9f92f29d64b9fc2aca15437027dfb209157a25ee0a3b260b0b0e73f2eea99c9ab31fbe69e3db50cdfc689f701ec2359c",
        None,
    ),
)

INVALID_PATHS = (
    "m/83696968h",  # missing application
    "m/83696968/39h/0h/12h/0h",  # purpose not hardened
    "m/83696968h/39h/0h/12h/0",  # index not hardened
    "m/44h/0h/0h",  # not a BIP-85 path
    "m/83696968h/39h/0h/12h",  # missing index
    "m/83696968h/39h/0h/13h/0h",  # invalid number of words
    "m/83696968h/39h/1h/12h/0h",  # unsupported language
    "m/83696968h/2h/0h/0h",  # too many components for WIF
    "m/83696968h/32h",  # missing index for xprv
    "m/83696968h/128169h/8h/0h",  # too few bytes
    "m/83696968h/128169h/65h/0h",  # too many bytes
    "m/83696968h/707764h/19h/0h",  # password too short
    "m/83696968h/707764h/87h/0h",  # password too long
    "m/83696968h/707785h/9h/0h",  # password too short
    "m/83696968h/707785h/81h/0h",  # password too long
    "m/83696968h/0h/0h/0h/0h/0h/0h/0h/0h",  # too long
)


@pytest.mark.parametrize("path, entropy, secret", VECTORS)
def test_get_bip85_entropy(session: Session, path: str, entropy: str, secret: str):
    result = misc.get_bip85_entropy(session, parse_path(path))
    assert result.entropy.hex() == entropy
    assert result.secret == secret


@pytest.mark.parametrize("path", INVALID_PATHS)
def test_get_bip85_entropy_invalid_path(session: Session, path: str):
    with pytest.raises(TrezorFailure, match="DataError"):
        misc.get_bip85_entropy(session, parse_path(path))


@pytest.mark.parametrize("path, entropy, secret", VECTORS[4:])
def test_get_bip85_entropy_show_display(
    session: Session, path: str, entropy: str, secret: str
):
    result = misc.get_bip85_entropy(session, parse_path(path), show_display=True)
    assert result.entropy.hex() == entropy
    assert result.secret == secret


@pytest.mark.parametrize("on_device_only", (False, True))
def test_get_bip85_entropy_show_mnemonic(session: Session, on_device_only: bool):
    path, entropy, secret = VECTORS[1]
    debug = session.debug

    def input_flow():
        # confirm application and derivation path
        yield
        debug.press_yes()

        if not on_device_only:
            # confirm sending the secret to the host
            yield
            debug.press_yes()

        if debug.layout_type is LayoutType.Bolt:
            words = yield from read_mnemonic_from_screen_bolt(debug)
        elif debug.layout_type is LayoutType.Caesar:
            words = yield from read_mnemonic_from_screen_caesar(debug)
        elif debug.layout_type is LayoutType.Delizia:
            words = yield from read_mnemonic_from_screen_delizia(debug)
        elif debug.layout_type is LayoutType.Eckhart:
            words = yield from read_mnemonic_from_screen_eckhart(debug)
        else:
            raise ValueError(f"Unknown layout: {debug.layout_type}")

        assert " ".join(words) == secret

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        result = misc.get_bip85_entropy(
            session,
            parse_path(path),
            show_display=True,
            on_device_only=on_device_only,
        )

    if on_device_only:
        assert result == messages.Bip85Entropy()
    else:
        assert result.entropy.hex() == entropy
        assert result.secret == secret


def test_get_bip85_entropy_cancel(session: Session):
    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        misc.get_bip85_entropy(session, parse_path(VECTORS[1][0]))
