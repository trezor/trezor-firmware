from itertools import combinations
from unittest import mock

import pytest
import shamir_mnemonic as shamir
from shamir_mnemonic import MnemonicError

from trezorlib import device, messages as proto
from trezorlib.messages import BackupType, ButtonRequestType as B

from .common import TrezorTest, generate_entropy

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


@pytest.mark.skip_t1
class TestMsgResetDeviceT2(TrezorTest):
    # TODO: test with different options
    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_shamir(self, client):
        strength = 128
        member_threshold = 3
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
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.EntropyRequest(),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Success),
                    proto.Success(),
                    proto.Features(),
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

        # generate secret locally
        internal_entropy = client.debug.state().reset_entropy
        secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

        # validate that all combinations will result in the correct master secret
        validate_mnemonics(all_mnemonics, member_threshold, secret)

        # Check if device is properly initialized
        assert client.features.initialized is True
        assert client.features.needs_backup is False
        assert client.features.pin_protection is False
        assert client.features.passphrase_protection is False


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # We expect these combinations to recreate the secret properly
    for test_group in combinations(mnemonics, threshold):
        # TODO: HOTFIX, we should fix this properly by modifying and unifying the python-shamir-mnemonic API
        ms = shamir.combine_mnemonics(test_group)
        identifier, iteration_exponent, _, _, _ = shamir._decode_mnemonics(test_group)
        ems = shamir._encrypt(ms, b"", iteration_exponent, identifier)
        assert ems == expected_ems
    # We expect these combinations to raise MnemonicError
    for test_group in combinations(mnemonics, threshold - 1):
        with pytest.raises(
            MnemonicError, match=r".*Expected {} mnemonics.*".format(threshold)
        ):
            shamir.combine_mnemonics(test_group)
