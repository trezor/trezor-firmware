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

from unittest import mock

import pytest
from shamir_mnemonic import shamir

from trezorlib import device, messages as proto
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupType, ButtonRequestType as B

from ..common import (
    click_through,
    generate_entropy,
    paging_responses,
    read_and_confirm_mnemonic,
)

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


@pytest.mark.skip_t1
class TestMsgResetDeviceT2:
    # TODO: test with different options
    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_slip39_advanced(self, client):
        strength = 128
        word_count = 20
        mnemonic_page_count = (word_count // 4) + 1
        member_threshold = 3
        all_mnemonics = []

        def input_flow():
            # 1. Confirm Reset
            # 2. Backup your seed
            # 3. Confirm warning
            # 4. shares info
            # 5. Set & Confirm number of groups
            # 6. threshold info
            # 7. Set & confirm group threshold value
            # 8-17: for each of 5 groups:
            #   1. Set & Confirm number of shares
            #   2. Set & confirm share threshold value
            # 18. Confirm show seeds
            yield from click_through(client.debug, screens=18, code=B.ResetDevice)

            # show & confirm shares for all groups
            for g in range(5):
                for h in range(5):
                    # mnemonic phrases
                    mnemonic = yield from read_and_confirm_mnemonic(client.debug)
                    all_mnemonics.append(mnemonic)

                    # Confirm continue to next share
                    br = yield
                    assert br.code == B.Success
                    client.debug.press_yes()

            # safety warning
            br = yield
            assert br.code == B.Success
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
                    proto.ButtonRequest(code=B.ResetDevice),  # group #1 counts
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),  # group #2 counts
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),  # group #3 counts
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),  # group #4 counts
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),  # group #5 counts
                    proto.ButtonRequest(code=B.ResetDevice),
                ]
                + [
                    # individual mnemonic
                    *paging_responses(mnemonic_page_count, code=B.ResetDevice),
                    proto.ButtonRequest(code=B.Success),
                ]
                * (5 * 5)  # groups * shares
                + [
                    proto.ButtonRequest(code=B.Success),
                    proto.Success,
                    proto.Features,
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
                language="en-US",
                backup_type=BackupType.Slip39_Advanced,
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
        assert client.features.backup_type is BackupType.Slip39_Advanced

        # backup attempt fails because backup was done in reset
        with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
            device.backup(client)


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # 3of5 shares 3of5 groups
    # TODO: test all possible group+share combinations?
    test_combination = mnemonics[0:3] + mnemonics[5:8] + mnemonics[10:13]
    groups = shamir.decode_mnemonics(test_combination)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
