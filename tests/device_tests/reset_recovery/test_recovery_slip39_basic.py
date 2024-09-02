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

from ...common import (
    MNEMONIC_SLIP39_BASIC_20_3of6,
    MNEMONIC_SLIP39_BASIC_20_3of6_SECRET,
    MNEMONIC_SLIP39_BASIC_EXT_20_2of3,
    MNEMONIC_SLIP39_BASIC_EXT_20_2of3_SECRET,
)
from ...input_flows import (
    InputFlowSlip39BasicRecovery,
    InputFlowSlip39BasicRecoveryAbort,
    InputFlowSlip39BasicRecoveryAbortBetweenShares,
    InputFlowSlip39BasicRecoveryInvalidFirstShare,
    InputFlowSlip39BasicRecoveryInvalidSecondShare,
    InputFlowSlip39BasicRecoveryNoAbort,
    InputFlowSlip39BasicRecoverySameShare,
    InputFlowSlip39BasicRecoveryWrongNthWord,
)

pytestmark = pytest.mark.models("core")

MNEMONIC_SLIP39_BASIC_20_1of1 = [
    "academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic rebuild aquatic spew"
]


MNEMONIC_SLIP39_BASIC_33_2of5 = [
    "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
    "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
]

VECTORS = (
    (
        MNEMONIC_SLIP39_BASIC_20_3of6,
        MNEMONIC_SLIP39_BASIC_20_3of6_SECRET,
        messages.BackupType.Slip39_Basic,
    ),
    (
        MNEMONIC_SLIP39_BASIC_EXT_20_2of3,
        MNEMONIC_SLIP39_BASIC_EXT_20_2of3_SECRET,
        messages.BackupType.Slip39_Basic_Extendable,
    ),
    (
        MNEMONIC_SLIP39_BASIC_33_2of5,
        "b770e0da1363247652de97a39bdbf2463be087848d709ecbf28e84508e31202a",
        messages.BackupType.Slip39_Basic,
    ),
)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("shares, secret, backup_type", VECTORS)
def test_secret(
    client: Client, shares: list[str], secret: str, backup_type: messages.BackupType
):
    with client:
        IF = InputFlowSlip39BasicRecovery(client, shares)
        client.set_input_flow(IF.get())
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is backup_type

    # Check mnemonic
    assert client.debug.state().mnemonic_secret.hex() == secret


@pytest.mark.setup_client(uninitialized=True)
def test_recover_with_pin_passphrase(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecovery(
            client, MNEMONIC_SLIP39_BASIC_20_3of6, pin="654"
        )
        client.set_input_flow(IF.get())
        ret = device.recover(
            client,
            pin_protection=True,
            passphrase_protection=True,
            label="label",
        )

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True
    assert client.features.backup_type is messages.BackupType.Slip39_Basic


@pytest.mark.setup_client(uninitialized=True)
def test_abort(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecoveryAbort(client)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_abort_between_shares(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecoveryAbortBetweenShares(
            client, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_noabort(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecoveryNoAbort(client, MNEMONIC_SLIP39_BASIC_20_3of6)
        client.set_input_flow(IF.get())
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True


@pytest.mark.setup_client(uninitialized=True)
def test_invalid_mnemonic_first_share(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecoveryInvalidFirstShare(client)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_invalid_mnemonic_second_share(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecoveryInvalidSecondShare(
            client, MNEMONIC_SLIP39_BASIC_20_3of6
        )
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("nth_word", range(3))
def test_wrong_nth_word(client: Client, nth_word: int):
    share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
    with client:
        IF = InputFlowSlip39BasicRecoveryWrongNthWord(client, share, nth_word)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_same_share(client: Client):
    share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
    with client:
        IF = InputFlowSlip39BasicRecoverySameShare(client, share)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_1of1(client: Client):
    with client:
        IF = InputFlowSlip39BasicRecovery(client, MNEMONIC_SLIP39_BASIC_20_1of1)
        client.set_input_flow(IF.get())
        ret = device.recover(
            client,
            pin_protection=False,
            passphrase_protection=False,
            label="label",
        )

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.initialized is True
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Basic
