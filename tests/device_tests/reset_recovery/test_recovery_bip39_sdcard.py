import pytest

from trezorlib import device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...common import MNEMONIC12
from ...input_flows import InputFlowBip39RecoverySdCard

pytestmark = [pytest.mark.skip_t1, pytest.mark.skip_tr]


def prepare_data_for_sdcard() -> bytes:
    # MNEMONIC12 backup block
    backup_block_str = "54525A4D000000004C616C636F686F6C20776F6D616E206162757365206D75737420647572696E67206D6F6E69746F72206E6F626C652061637475616C206D6978656420747261646520616E676572206169736C654B1118DAD99C3A21E85AC1CBAE3D41F8BA02BE5E6B8422B3225C9DB53C316D8A"
    return bytes.fromhex(backup_block_str)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.sd_card(formatted=False)
def test_sdrecover_tt_nopin_nopassphrase(client: Client):
    with client:
        # put seed writing directly to the first backup block
        mnemonic_data_bytes = prepare_data_for_sdcard()
        backup_block = messages.DebugLinkSdCardDataBlock(
            number=65525 + 552 + 63, data=mnemonic_data_bytes
        )
        client.debug.insert_sd_card(serial_number=1, data_blocks=[backup_block])

        IF = InputFlowBip39RecoverySdCard(client)
        client.set_input_flow(IF.get())
        device.recover(
            client,
            pin_protection=False,
            passphrase_protection=False,
            label="SD recovery",
        )

    assert client.debug.state().mnemonic_secret.decode() == MNEMONIC12

    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Bip39
    assert client.features.label == "SD recovery"
