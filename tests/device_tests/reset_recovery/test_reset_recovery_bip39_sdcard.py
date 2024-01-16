import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType
from trezorlib.tools import parse_path

from ...common import WITH_MOCK_URANDOM
from ...input_flows import InputFlowBip39RecoverySdCard, InputFlowBip39ResetBackupSdCard

pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_tr]

# NOTE: Test adapted from test_reset_recovery_bip39.py


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.sd_card(formatted=False)
def test_reset_recovery_sdcard(client: Client):
    reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))

    device.wipe(client)
    recover(client)
    address_after = btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))
    assert address_before == address_after


def reset(client: Client, strength: int = 128, skip_backup: bool = False) -> None:
    with WITH_MOCK_URANDOM, client:
        IF = InputFlowBip39ResetBackupSdCard(client)
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
            backup_type=BackupType.Bip39,
        )

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False



def recover(client: Client):
    with client:
        IF = InputFlowBip39RecoverySdCard(client)
        client.set_input_flow(IF.get())
        client.watch_layout()
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
