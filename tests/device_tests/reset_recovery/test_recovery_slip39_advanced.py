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

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...common import MNEMONIC_SLIP39_ADVANCED_20, MNEMONIC_SLIP39_ADVANCED_33
from ...input_flows import (
    InputFlowSlip39AdvancedRecovery,
    InputFlowSlip39AdvancedRecoveryAbort,
    InputFlowSlip39AdvancedRecoveryNoAbort,
    InputFlowSlip39AdvancedRecoveryShareAlreadyEntered,
    InputFlowSlip39AdvancedRecoveryThresholdReached,
)

pytestmark = pytest.mark.models("core")

EXTRA_GROUP_SHARE = [
    "eraser senior decision smug corner ruin rescue cubic angel tackle skin skunk program roster trash rumor slush angel flea amazing"
]

# secrets generated using model T
VECTORS = (
    (MNEMONIC_SLIP39_ADVANCED_20, "c2d2e26ad06023c60145f150abe2dd2b"),
    (
        MNEMONIC_SLIP39_ADVANCED_33,
        "c41d5cf80fed71a008a3a0ae0458ff0c6d621b1a5522bccbfedbcfad87005c06",
    ),
)


# To allow reusing functionality for multiple tests
def _test_secret(
    client: Client, shares: list[str], secret: str, click_info: bool = False
):
    with client:
        IF = InputFlowSlip39AdvancedRecovery(client, shares, click_info=click_info)
        client.set_input_flow(IF.get())
        device.recover(
            client,
            pin_protection=False,
            passphrase_protection=False,
            label="label",
        )

    assert client.features.initialized is True
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Advanced
    assert client.debug.state().mnemonic_secret.hex() == secret


@pytest.mark.parametrize("shares, secret", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_secret(client: Client, shares: list[str], secret: str):
    _test_secret(client, shares, secret)


@pytest.mark.parametrize("shares, secret", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models(skip="safe3", reason="safe3 does not have info button")
def test_secret_click_info_button(client: Client, shares: list[str], secret: str):
    _test_secret(client, shares, secret, click_info=True)


@pytest.mark.setup_client(uninitialized=True)
def test_extra_share_entered(client: Client):
    _test_secret(
        client,
        shares=EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20,
        secret=VECTORS[0][1],
    )


@pytest.mark.setup_client(uninitialized=True)
def test_abort(client: Client):
    with client:
        IF = InputFlowSlip39AdvancedRecoveryAbort(client)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_noabort(client: Client):
    with client:
        IF = InputFlowSlip39AdvancedRecoveryNoAbort(
            client, EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20
        )
        client.set_input_flow(IF.get())
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True


@pytest.mark.setup_client(uninitialized=True)
def test_same_share(client: Client):
    # we choose the second share from the fixture because
    # the 1st is 1of1 and group threshold condition is reached first
    first_share = MNEMONIC_SLIP39_ADVANCED_20[1].split(" ")
    # second share is first 4 words of first
    second_share = MNEMONIC_SLIP39_ADVANCED_20[1].split(" ")[:4]

    with client:
        IF = InputFlowSlip39AdvancedRecoveryShareAlreadyEntered(
            client, first_share, second_share
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_group_threshold_reached(client: Client):
    # first share in the fixture is 1of1 so we choose that
    first_share = MNEMONIC_SLIP39_ADVANCED_20[0].split(" ")
    # second share is first 3 words of first
    second_share = MNEMONIC_SLIP39_ADVANCED_20[0].split(" ")[:3]

    with client:
        IF = InputFlowSlip39AdvancedRecoveryThresholdReached(
            client, first_share, second_share
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
