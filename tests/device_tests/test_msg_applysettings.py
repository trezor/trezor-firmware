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

import pytest

from trezorlib import btc, device, exceptions, messages
from trezorlib.tools import parse_path

EXPECTED_RESPONSES_NOPIN = [
    messages.ButtonRequest(),
    messages.Success,
    messages.Features,
]
EXPECTED_RESPONSES_PIN_T1 = [messages.PinMatrixRequest()] + EXPECTED_RESPONSES_NOPIN
EXPECTED_RESPONSES_PIN_TT = [messages.ButtonRequest()] + EXPECTED_RESPONSES_NOPIN

PIN4 = "1234"


def _set_expected_responses(client):
    client.use_pin_sequence([PIN4])
    if client.features.model == "1":
        client.set_expected_responses(EXPECTED_RESPONSES_PIN_T1)
    else:
        client.set_expected_responses(EXPECTED_RESPONSES_PIN_TT)


@pytest.mark.setup_client(pin=PIN4)
class TestMsgApplysettings:
    def test_apply_settings(self, client):
        assert client.features.label == "test"

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, label="new label")

        assert client.features.label == "new label"

    @pytest.mark.skip_t1
    def test_apply_settings_rotation(self, client):
        assert client.features.display_rotation is None

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, display_rotation=270)

        assert client.features.display_rotation == 270

    @pytest.mark.skip_t2
    def test_invalid_language(self, client):
        assert client.features.language == "en-US"

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, language="nonexistent")

        assert client.features.language == "en-US"

    @pytest.mark.setup_client(pin=PIN4, passphrase=False)
    def test_apply_settings_passphrase(self, client):
        assert client.features.passphrase_protection is False

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, use_passphrase=True)

        assert client.features.passphrase_protection is True

        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, use_passphrase=False)

        assert client.features.passphrase_protection is False

        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, use_passphrase=True)

        assert client.features.passphrase_protection is True

    @pytest.mark.setup_client(passphrase=False)
    @pytest.mark.skip_t1
    def test_apply_settings_passphrase_on_device(self, client):
        # enable passphrase
        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, use_passphrase=True)

        assert client.features.passphrase_protection is True

        # enable force on device
        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, passphrase_always_on_device=True)

        assert client.features.passphrase_protection is True
        assert client.features.passphrase_always_on_device is True

        # turning off the passphrase should also clear the always_on_device setting
        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, use_passphrase=False)

        assert client.features.passphrase_protection is False
        assert client.features.passphrase_always_on_device is False

        # and turning it back on does not modify always_on_device
        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, use_passphrase=True)

        assert client.features.passphrase_protection is True
        assert client.features.passphrase_always_on_device is False

    @pytest.mark.skip_t1
    def test_apply_homescreen_toif(self, client):
        img = b"TOIf\x90\x00\x90\x00~\x00\x00\x00\xed\xd2\xcb\r\x83@\x10D\xc1^.\xde#!\xac31\x99\x10\x8aC%\x14~\x16\x92Y9\x02WI3\x01<\xf5cI2d\x1es(\xe1[\xdbn\xba\xca\xe8s7\xa4\xd5\xd4\xb3\x13\xbdw\xf6:\xf3\xd1\xe7%\xc7]\xdd_\xb3\x9e\x9f\x9e\x9fN\xed\xaaE\xef\xdc\xcf$D\xa7\xa4X\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0OV"

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, homescreen=img)

            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(client, homescreen=b"")

    @pytest.mark.parametrize(
        "toif_data",
        [
            # incomplete header
            b"TOIf\x90\00\x90\x00~"
            # wrong magic
            b"XXXf\x90\x00\x90\x00~\x00\x00\x00\xed\xd2\xcb\r\x83@\x10D\xc1^.\xde#!\xac31\x99\x10\x8aC%\x14~\x16\x92Y9\x02WI3\x01<\xf5cI2d\x1es(\xe1[\xdbn\xba\xca\xe8s7\xa4\xd5\xd4\xb3\x13\xbdw\xf6:\xf3\xd1\xe7%\xc7]\xdd_\xb3\x9e\x9f\x9e\x9fN\xed\xaaE\xef\xdc\xcf$D\xa7\xa4X\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0OV"
            # wrong datasize in header
            b"TOIf\x90\x00\x90\x00~\x00\x00\x00\xed\xd2\xcb\r\x83@\x10D\xc1^.\xde#!\xac31\x99\x10\x8aC%\x14~\x16\x92Y9\x02WI3\x01<\xf5cI2d\x1es(\xe1[\xdbn\xba\xca\xe8s7\xa4\xd5\xd4\xb3\x13\xbdw\xf6:\xf3\xd1\xe7%\xc7]\xdd_\xb3\x9e\x9f\x9e\x9fN\xed\xaaE\xef\xdc\xcf$D\xa7\xa4X\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            # grayscale 144x144
            b"TOIg\x90\x00\x90\x00~\x00\x00\x00\xed\xd2\xcb\r\x83@\x10D\xc1^.\xde#!\xac31\x99\x10\x8aC%\x14~\x16\x92Y9\x02WI3\x01<\xf5cI2d\x1es(\xe1[\xdbn\xba\xca\xe8s7\xa4\xd5\xd4\xb3\x13\xbdw\xf6:\xf3\xd1\xe7%\xc7]\xdd_\xb3\x9e\x9f\x9e\x9fN\xed\xaaE\xef\xdc\xcf$D\xa7\xa4X\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0OV",
            # fullcolor 128x128
            b"TOIf\x80\x00\x80\x00~\x00\x00\x00\xed\xd2\xcb\r\x83@\x10D\xc1^.\xde#!\xac31\x99\x10\x8aC%\x14~\x16\x92Y9\x02WI3\x01<\xf5cI2d\x1es(\xe1[\xdbn\xba\xca\xe8s7\xa4\xd5\xd4\xb3\x13\xbdw\xf6:\xf3\xd1\xe7%\xc7]\xdd_\xb3\x9e\x9f\x9e\x9fN\xed\xaaE\xef\xdc\xcf$D\xa7\xa4X\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0OV",
        ],
    )
    @pytest.mark.skip_t1
    def test_apply_homescreen_toif_fail(self, client, toif_data):
        with pytest.raises(exceptions.TrezorFailure), client:
            client.use_pin_sequence([PIN4])
            device.apply_settings(client, homescreen=toif_data)

    @pytest.mark.skip_t2
    def test_apply_homescreen(self, client):
        img = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"\x00\x00\x00\x00\x04\x80\x00\x00\x00\x00\x00\x00\x00\x00\x04\x88\x02\x00\x00\x00\x02\x91\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00\x90@\x00\x11@\x00\x00\x00\x00\x00\x00\x08\x00\x10\x92\x12\x04\x00\x00\x05\x12D\x00\x00\x00\x00\x00 \x00\x00\x08\x00Q\x00\x00\x02\xc0\x00\x00\x00\x00\x00\x00\x00\x10\x02 \x01\x04J\x00)$\x00\x00\x00\x00\x80\x00\x00\x00\x00\x08\x10\xa1\x00\x00\x02\x81 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\tP\x00\x00\x00\x00\x00\x00 \x00\x00\xa0\x00\xa0R \x12\x84\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x08\x00\tP\x00\x00\x00\x00 \x00\x04 \x00\x80\x02\x00@\x02T\xc2 \x00\x00\x00\x00\x00\x00\x00\x10@\x00)\t@\n\xa0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x80@\x14\xa9H\x04\x00\x00\x88@\x00\x00\x00\x00\x00\x02\x02$\x00\x15B@\x00\nP\x00\x00\x00\x00\x00\x80\x00\x00\x91\x01UP\x00\x00 \x02\x00\x00\x00\x00\x00\x00\x02\x08@ Z\xa5 \x00\x00\x80\x00\x00\x00\x00\x00\x00\x08\xa1%\x14*\xa0\x00\x00\x02\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00@\xaa\x91 \x00\x05E\x80\x00\x00\x00\x00\x00\x02*T\x05-D\x00\x00\x05 @\x00\x00\x00\x00\x00%@\x80\x11V\xa0\x88\x00\x05@\xb0\x00\x00\x00\x00\x00\x818$\x04\xabD \x00\x06\xa1T\x00\x00\x00\x00\x02\x03\xb8\x01R\xd5\x01\x00\x00\x05AP\x00\x00\x00\x00\x08\xadT\x00\x05j\xa4@\x00\x87ah\x00\x00\x00\x00\x02\x8d\xb8\x08\x00.\x01\x00\x00\x02\xa5\xa8\x10\x00\x00\x00*\xc1\xec \n\xaa\x88 \x02@\xf6\xd0\x02\x00\x00\x00\x0bB\xb6\x14@U"\x80\x00\x01{`\x00\x00\x00\x00M\xa3\xf8 \x15*\x00\x00\x00\x10n\xc0\x04\x00\x00\x02\x06\xc2\xa8)\x00\x96\x84\x80\x00\x00\x1b\x00\x00\x80@\x10\x87\xa7\xf0\x84\x10\xaa\x10\x00\x00D\x00\x00\x02 \x00\x8a\x06\xfa\xe0P\n-\x02@\x00\x12\x00\x00\x00\x00\x10@\x83\xdf\xa0\x00\x08\xaa@\x00\x00\x01H\x00\x05H\x04\x12\x01\xf7\x81P\x02T\t\x00\x00\x00 \x00\x00\x84\x10\x00\x00z\x00@)* \x00\x00\x01\n\xa0\x02 \x05\n\x00\x00\x05\x10\x84\xa8\x84\x80\x00\x00@\x14\x00\x92\x10\x80\x00\x04\x11@\tT\x00\x00\x00\x00\n@\x00\x08\x84@$\x00H\x00\x12Q\x02\x00\x00\x00\x00\x90\x02A\x12\xa8\n\xaa\x92\x10\x04\xa8\x10@\x00\x00\x04\x04\x00\x04I\x00\x04\x14H\x80"R\x01\x00\x00\x00!@\x00\x00$\xa0EB\x80\x08\x95hH\x00\x00\x00\x84\x10 \x05Z\x00\x00(\x00\x02\x00\xa1\x01\x00\x00\x04\x00@\x82\x00\xadH*\x92P\x00\xaaP\x00\x00\x00\x00\x11\x02\x01*\xad\x01\x00\x01\x01"\x11D\x08\x00\x00\x10\x80 \x00\x81W\x80J\x94\x04\x08\xa5 !\x00\x00\x00\x02\x00B*\xae\xa1\x00\x80\x10\x01\x08\xa4\x00\x00\x00\x00\x00\x84\x00\t[@"HA\x04E\x00\x84\x00\x00\x00\x10\x00\x01J\xd5\x82\x90\x02\x00!\x02\xa2\x00\x00\x00\x00\x00\x00\x00\x05~\xa0\x00 \x10\n)\x00\x11\x00\x00\x00\x00\x00\x00!U\x80\xa8\x88\x82\x80\x01\x00\x00\x00\x00\x00\x00H@\x11\xaa\xc0\x82\x00 *\n\x00\x00\x00\x00\x00\x00\x00\x00\n\xabb@ \x04\x00! \x84\x00\x00\x00\x00\x02@\xa5\x15A$\x04\x81(\n\x00\x00\x00\x00\x00\x00 \x01\x10\x02\xe0\x91\x02\x00\x00\x04\x00\x00\x00\x00\x00\x00\x01 \xa9\tQH@\x91 P\x00\x00\x00\x00\x00\x00\x08\x00\x00\xa0T\xa5\x00@\x80\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"\x00\x00\x00\x00\xa2\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00 T\xa0\t\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00@\x02\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00*\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x10\x00\x00\x10\x02\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00@\x04\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x08@\x10\x00\x00\x00\x00'

        with client:
            _set_expected_responses(client)
            device.apply_settings(client, homescreen=img)

    @pytest.mark.skip_t1
    @pytest.mark.setup_client(pin=None)
    def test_safety_checks(self, client):
        def get_bad_address():
            btc.get_address(client, "Bitcoin", parse_path("m/0"))

        assert client.features.safety_checks == messages.SafetyCheckLevel.Strict

        with pytest.raises(
            exceptions.TrezorFailure, match="Forbidden key path"
        ), client:
            client.set_expected_responses([messages.Failure])
            get_bad_address()

        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(
                client, safety_checks=messages.SafetyCheckLevel.PromptAlways
            )

        assert client.features.safety_checks == messages.SafetyCheckLevel.PromptAlways

        with client:
            client.set_expected_responses([messages.Address])
            get_bad_address()

        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(
                client, safety_checks=messages.SafetyCheckLevel.Strict
            )

        assert client.features.safety_checks == messages.SafetyCheckLevel.Strict

        with pytest.raises(
            exceptions.TrezorFailure, match="Forbidden key path"
        ), client:
            client.set_expected_responses([messages.Failure])
            get_bad_address()

        with client:
            client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(
                client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
            )

        assert (
            client.features.safety_checks == messages.SafetyCheckLevel.PromptTemporarily
        )

        with client:
            client.set_expected_responses([messages.Address])
            get_bad_address()

    @pytest.mark.skip_t1
    def test_experimental_features(self, client):
        def experimental_call():
            btc.authorize_coinjoin(
                client,
                coordinator="www.example.com",
                max_total_fee=10010,
                fee_per_anonymity=5000000,  # 0.005 %
                n=parse_path("m/84'/1'/0'"),
                coin_name="Testnet",
                script_type=messages.InputScriptType.SPENDWITNESS,
            )

        assert client.features.experimental_features is None

        # unlock
        with client:
            _set_expected_responses(client)
            device.apply_settings(client, label="new label")

        assert client.features.experimental_features

        with client:
            client.set_expected_responses(
                [messages.ButtonRequest, messages.ButtonRequest, messages.Success]
            )
            experimental_call()

        # relock and try again
        client.lock()
        with client:
            client.use_pin_sequence([PIN4])
            client.set_expected_responses(
                [
                    messages.ButtonRequest,
                    messages.ButtonRequest,
                    messages.ButtonRequest,
                    messages.Success,
                ]
            )
            experimental_call()

        # unset experimental features
        with client:
            client.set_expected_responses([messages.Success, messages.Features])
            device.apply_settings(client, experimental_features=False)

        assert not client.features.experimental_features

        with pytest.raises(exceptions.TrezorFailure, match="DataError"), client:
            client.set_expected_responses([messages.Failure])
            experimental_call()

    @pytest.mark.setup_client(pin=None)
    def test_label_too_long(self, client):
        with pytest.raises(exceptions.TrezorFailure), client:
            client.set_expected_responses([messages.Failure])
            device.apply_settings(client, label="A" * 33)
