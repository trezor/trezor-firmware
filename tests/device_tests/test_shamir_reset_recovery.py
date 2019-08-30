import pytest

from trezorlib import btc, device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B
from trezorlib.tools import parse_path

from .common import recovery_enter_shares


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

    def input_flow():
        # Confirm Reset
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # Backup your seed
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # Confirm warning
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # shares info
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # Set & Confirm number of shares
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # threshold info
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # Set & confirm threshold value
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # Confirm show seeds
        btn_code = yield
        assert btn_code == B.ResetDevice
        client.debug.press_yes()

        # show & confirm shares
        for h in range(5):
            words = []
            btn_code = yield
            assert btn_code == B.Other

            # mnemonic phrases
            # 20 word over 6 pages for strength 128, 33 words over 9 pages for strength 256
            for i in range(6):
                words.extend(client.debug.read_reset_word().split())
                if i < 5:
                    client.debug.swipe_down()
                else:
                    # last page is confirmation
                    client.debug.press_yes()

            # check share
            for _ in range(3):
                index = client.debug.read_reset_word_pos()
                client.debug.input(words[index])

            all_mnemonics.extend([" ".join(words)])

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
            backup_type=BackupType.Slip39_Basic,
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
