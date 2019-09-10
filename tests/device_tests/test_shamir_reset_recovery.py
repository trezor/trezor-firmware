import pytest

from trezorlib import btc, device, messages
from trezorlib.messages import ButtonRequestType as B, ResetDeviceBackupType
from trezorlib.tools import parse_path

from .common import click_through, read_and_confirm_mnemonic, recovery_enter_shares


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_reset_recovery(client):
    mnemonics = reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))

    for share_subset in ((0, 1, 2), (4, 3, 2), (2, 1, 3)):
        # TODO: change the above to itertools.combinations(mnemonics, 3)
        device.wipe(client)
        selected_mnemonics = [mnemonics[i] for i in share_subset]
        recover(client, selected_mnemonics)
        address_after = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
        assert address_before == address_after


def reset(client, strength=128):
    all_mnemonics = []
    # per SLIP-39: strength in bits, rounded up to nearest multiple of 10, plus 70 bits
    # of metadata, split into 10-bit words
    word_count = ((strength + 9) // 10) + 7

    def input_flow():
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of shares
        # 6. threshold info
        # 7. Set & confirm threshold value
        # 8. Confirm show seeds
        yield from click_through(client.debug, screens=8, code=B.ResetDevice)

        # show & confirm shares
        for h in range(5):
            # mnemonic phrases
            btn_code = yield
            assert btn_code == B.Other
            mnemonic = read_and_confirm_mnemonic(client.debug, words=word_count)
            all_mnemonics.append(mnemonic)

            # Confirm continue to next share
            btn_code = yield
            assert btn_code == B.Success
            client.debug.press_yes()

        # safety warning
        btn_code = yield
        assert btn_code == B.Success
        client.debug.press_yes()

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Other),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Other),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Other),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Other),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Other),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
                messages.Features(),
            ]
        )
        client.set_input_flow(input_flow)

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="english",
            backup_type=ResetDeviceBackupType.Slip39_Single_Group,
        )

    client.set_input_flow(None)

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    return all_mnemonics


def recover(client, shares):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(debug, shares)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    client.set_input_flow(None)

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
