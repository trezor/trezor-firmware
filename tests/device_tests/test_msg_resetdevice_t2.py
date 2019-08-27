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
from mnemonic import Mnemonic

from trezorlib import device, messages as proto
from trezorlib.messages import ButtonRequestType as B

from .common import MNEMONIC12, TrezorTest, generate_entropy

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


@pytest.mark.skip_t1
class TestMsgResetDeviceT2(TrezorTest):
    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device(self, client):
        words = []
        strength = 128

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

            # mnemonic phrases
            btn_code = yield
            assert btn_code == B.ResetDevice
            # 12 words, 3 pages
            for i in range(3):
                words.extend(client.debug.read_reset_word().split())
                if i < 2:
                    client.debug.swipe_down()
                else:
                    # last page is confirmation
                    client.debug.press_yes()

            # check backup words
            for _ in range(3):
                index = client.debug.read_reset_word_pos()
                client.debug.input(words[index])

            # confirm recovery seed check
            btn_code = yield
            assert btn_code == B.Success
            client.debug.press_yes()

            # confirm success
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
            )

        # generate mnemonic locally
        internal_entropy = client.debug.state().reset_entropy
        entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
        expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

        # Compare that device generated proper mnemonic for given entropies
        assert " ".join(words) == expected_mnemonic

        # Check if device is properly initialized
        resp = client.call_raw(proto.Initialize())
        assert resp.initialized is True
        assert resp.needs_backup is False
        assert resp.pin_protection is False
        assert resp.passphrase_protection is False

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_pin(self, client):
        words = []
        strength = 128

        def input_flow():
            # Confirm Reset
            btn_code = yield
            assert btn_code == B.ResetDevice
            client.debug.press_yes()

            # Enter new PIN
            yield
            client.debug.input("654")

            # Confirm PIN
            yield
            client.debug.input("654")

            # Confirm entropy
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

            # mnemonic phrases
            btn_code = yield
            assert btn_code == B.ResetDevice
            # 12 words, 3 pages
            for i in range(3):
                words.extend(client.debug.read_reset_word().split())
                if i < 2:
                    client.debug.swipe_down()
                else:
                    # last page is confirmation
                    client.debug.press_yes()

            # check backup words
            for _ in range(3):
                index = client.debug.read_reset_word_pos()
                client.debug.input(words[index])

            # confirm recovery seed check
            btn_code = yield
            assert btn_code == B.Success
            client.debug.press_yes()

            # confirm success
            btn_code = yield
            assert btn_code == B.Success
            client.debug.press_yes()

        os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
        with mock.patch("os.urandom", os_urandom), client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.Other),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.EntropyRequest(),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.ResetDevice),
                    proto.ButtonRequest(code=B.Success),
                    proto.ButtonRequest(code=B.Success),
                    proto.Success(),
                    proto.Features(),
                ]
            )
            client.set_input_flow(input_flow)

            # PIN, passphrase, display random
            device.reset(
                client,
                display_random=True,
                strength=strength,
                passphrase_protection=True,
                pin_protection=True,
                label="test",
                language="english",
            )

        # generate mnemonic locally
        internal_entropy = client.debug.state().reset_entropy
        entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
        expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

        # Compare that device generated proper mnemonic for given entropies
        assert " ".join(words) == expected_mnemonic

        # Check if device is properly initialized
        resp = client.call_raw(proto.Initialize())
        assert resp.initialized is True
        assert resp.needs_backup is False
        assert resp.pin_protection is True
        assert resp.passphrase_protection is True

    @pytest.mark.setup_client(uninitialized=True)
    def test_failed_pin(self, client):
        # external_entropy = b'zlutoucky kun upel divoke ody' * 2
        strength = 128
        ret = client.call_raw(
            proto.ResetDevice(strength=strength, pin_protection=True, label="test")
        )

        # Confirm Reset
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter PIN for first time
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.input("654")
        ret = client.call_raw(proto.ButtonAck())

        # Enter PIN for second time
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.input("456")
        ret = client.call_raw(proto.ButtonAck())

        assert isinstance(ret, proto.ButtonRequest)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_already_initialized(self, client):
        with pytest.raises(Exception):
            device.reset(client, False, 128, True, True, "label", "english")
