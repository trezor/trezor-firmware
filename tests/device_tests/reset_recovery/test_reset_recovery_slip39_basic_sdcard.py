import itertools

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType
from trezorlib.tools import parse_path

from ...common import WITH_MOCK_URANDOM
from ...input_flows import (
    InputFlowSlip39BasicRecoverySdCard,
    InputFlowSlip39BasicResetRecoverySdCard,
)

# NOTE: Test adapted from test_reset_recovery_slip39_basic.py

pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_tr]
sdcard_serial_numbers = [1, 2, 3, 4, 5]


@pytest.mark.setup_client(uninitialized=True)
@WITH_MOCK_URANDOM
def test_reset_recovery(client: Client):
    reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))

    for selected_sdcards in itertools.combinations(sdcard_serial_numbers, 3):
        device.wipe(client)
        recover(client, selected_sdcards)
        address_after = btc.get_address(
            client, "Bitcoin", parse_path("m/44h/0h/0h/0/0")
        )
        assert address_before == address_after


def reset(client: Client, strength: int = 128) -> list[str]:
    with client:
        IF = InputFlowSlip39BasicResetRecoverySdCard(client, sdcard_serial_numbers)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
            backup_type=BackupType.Slip39_Basic,
        )

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False


def recover(client: Client, sdcards: list[int]):
    with client:
        IF = InputFlowSlip39BasicRecoverySdCard(client, sdcards)
        client.set_input_flow(IF.get())
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
