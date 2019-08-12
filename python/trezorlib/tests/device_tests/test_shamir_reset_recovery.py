from unittest import mock

import pytest

from trezorlib import btc, device, messages
from trezorlib.messages import ButtonRequestType as B, ResetDeviceBackupType
from trezorlib.tools import parse_path

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


@pytest.mark.skip_t1
def test_reset(client):
    mnemonics = reset(client)
    client.set_input_flow(None)
    address_before = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))

    device.wipe(client)
    recover(client, mnemonics[:3])
    address_after = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
    assert address_before == address_after


def reset(client):
    strength = 128
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

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
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

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False

    return all_mnemonics


def recover(client, shares):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, shares)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False


# TODO: let's merge this with test_msg_recoverydevice_shamir.py
def enter_all_shares(debug, shares):
    word_count = len(shares[0].split(" "))

    # Homescreen - proceed to word number selection
    yield
    debug.press_yes()
    # Input word number
    code = yield
    assert code == B.MnemonicWordCount
    debug.input(str(word_count))
    # Homescreen - proceed to share entry
    yield
    debug.press_yes()
    # Enter shares
    for share in shares:
        code = yield
        assert code == B.MnemonicInput
        # Enter mnemonic words
        for word in share.split(" "):
            debug.input(word)

        # Homescreen - continue
        # or Homescreen - confirm success
        yield
        debug.press_yes()
