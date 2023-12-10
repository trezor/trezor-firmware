import pytest

from trezorlib import device
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType

pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_tr]


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.sd_card(formatted=False)
def test_sd_backup_end_to_end(client: Client):
    with client:
        device.reset(client, pin_protection=False, label="SD card")

    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Bip39

    with client:
        device.wipe(client)

    # assert client.features.initialized is False
    # assert client.features.no_backup is True

    with client:
        device.recover(client, pin_protection=False)

    state = client.debug.state()
    print(f"mnemonic is {state.mnemonic_secret}")
    # assert state.mnemonic_type is backup_type
    # assert state.mnemonic_secret == secret
