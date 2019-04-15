# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import time

import pytest

from trezorlib import device, messages as proto

from .common import TrezorTest
from .conftest import TREZOR_VERSION

EXPECTED_RESPONSES_NOPIN = [proto.ButtonRequest(), proto.Success(), proto.Features()]
EXPECTED_RESPONSES_PIN = [proto.PinMatrixRequest()] + EXPECTED_RESPONSES_NOPIN

if TREZOR_VERSION >= 2:
    EXPECTED_RESPONSES = EXPECTED_RESPONSES_NOPIN
else:
    EXPECTED_RESPONSES = EXPECTED_RESPONSES_PIN


class TestMsgApplysettings(TrezorTest):
    def test_apply_settings(self):
        self.setup_mnemonic_pin_passphrase()
        assert self.client.features.label == "test"

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES)
            device.apply_settings(self.client, label="new label")

        assert self.client.features.label == "new label"

    @pytest.mark.skip_t2
    def test_invalid_language(self):
        self.setup_mnemonic_pin_passphrase()
        assert self.client.features.language == "english"

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES)
            device.apply_settings(self.client, language="nonexistent")

        assert self.client.features.language == "english"

    def test_apply_settings_passphrase(self):
        self.setup_mnemonic_pin_nopassphrase()

        assert self.client.features.passphrase_protection is False

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES)
            device.apply_settings(self.client, use_passphrase=True)

        assert self.client.features.passphrase_protection is True

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(self.client, use_passphrase=False)

        assert self.client.features.passphrase_protection is False

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES_NOPIN)
            device.apply_settings(self.client, use_passphrase=True)

        assert self.client.features.passphrase_protection is True

    @pytest.mark.skip_t2
    def test_apply_homescreen(self):
        self.setup_mnemonic_pin_passphrase()

        img = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"\x00\x00\x00\x00\x04\x80\x00\x00\x00\x00\x00\x00\x00\x00\x04\x88\x02\x00\x00\x00\x02\x91\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00\x90@\x00\x11@\x00\x00\x00\x00\x00\x00\x08\x00\x10\x92\x12\x04\x00\x00\x05\x12D\x00\x00\x00\x00\x00 \x00\x00\x08\x00Q\x00\x00\x02\xc0\x00\x00\x00\x00\x00\x00\x00\x10\x02 \x01\x04J\x00)$\x00\x00\x00\x00\x80\x00\x00\x00\x00\x08\x10\xa1\x00\x00\x02\x81 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\tP\x00\x00\x00\x00\x00\x00 \x00\x00\xa0\x00\xa0R \x12\x84\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x08\x00\tP\x00\x00\x00\x00 \x00\x04 \x00\x80\x02\x00@\x02T\xc2 \x00\x00\x00\x00\x00\x00\x00\x10@\x00)\t@\n\xa0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x80@\x14\xa9H\x04\x00\x00\x88@\x00\x00\x00\x00\x00\x02\x02$\x00\x15B@\x00\nP\x00\x00\x00\x00\x00\x80\x00\x00\x91\x01UP\x00\x00 \x02\x00\x00\x00\x00\x00\x00\x02\x08@ Z\xa5 \x00\x00\x80\x00\x00\x00\x00\x00\x00\x08\xa1%\x14*\xa0\x00\x00\x02\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00@\xaa\x91 \x00\x05E\x80\x00\x00\x00\x00\x00\x02*T\x05-D\x00\x00\x05 @\x00\x00\x00\x00\x00%@\x80\x11V\xa0\x88\x00\x05@\xb0\x00\x00\x00\x00\x00\x818$\x04\xabD \x00\x06\xa1T\x00\x00\x00\x00\x02\x03\xb8\x01R\xd5\x01\x00\x00\x05AP\x00\x00\x00\x00\x08\xadT\x00\x05j\xa4@\x00\x87ah\x00\x00\x00\x00\x02\x8d\xb8\x08\x00.\x01\x00\x00\x02\xa5\xa8\x10\x00\x00\x00*\xc1\xec \n\xaa\x88 \x02@\xf6\xd0\x02\x00\x00\x00\x0bB\xb6\x14@U"\x80\x00\x01{`\x00\x00\x00\x00M\xa3\xf8 \x15*\x00\x00\x00\x10n\xc0\x04\x00\x00\x02\x06\xc2\xa8)\x00\x96\x84\x80\x00\x00\x1b\x00\x00\x80@\x10\x87\xa7\xf0\x84\x10\xaa\x10\x00\x00D\x00\x00\x02 \x00\x8a\x06\xfa\xe0P\n-\x02@\x00\x12\x00\x00\x00\x00\x10@\x83\xdf\xa0\x00\x08\xaa@\x00\x00\x01H\x00\x05H\x04\x12\x01\xf7\x81P\x02T\t\x00\x00\x00 \x00\x00\x84\x10\x00\x00z\x00@)* \x00\x00\x01\n\xa0\x02 \x05\n\x00\x00\x05\x10\x84\xa8\x84\x80\x00\x00@\x14\x00\x92\x10\x80\x00\x04\x11@\tT\x00\x00\x00\x00\n@\x00\x08\x84@$\x00H\x00\x12Q\x02\x00\x00\x00\x00\x90\x02A\x12\xa8\n\xaa\x92\x10\x04\xa8\x10@\x00\x00\x04\x04\x00\x04I\x00\x04\x14H\x80"R\x01\x00\x00\x00!@\x00\x00$\xa0EB\x80\x08\x95hH\x00\x00\x00\x84\x10 \x05Z\x00\x00(\x00\x02\x00\xa1\x01\x00\x00\x04\x00@\x82\x00\xadH*\x92P\x00\xaaP\x00\x00\x00\x00\x11\x02\x01*\xad\x01\x00\x01\x01"\x11D\x08\x00\x00\x10\x80 \x00\x81W\x80J\x94\x04\x08\xa5 !\x00\x00\x00\x02\x00B*\xae\xa1\x00\x80\x10\x01\x08\xa4\x00\x00\x00\x00\x00\x84\x00\t[@"HA\x04E\x00\x84\x00\x00\x00\x10\x00\x01J\xd5\x82\x90\x02\x00!\x02\xa2\x00\x00\x00\x00\x00\x00\x00\x05~\xa0\x00 \x10\n)\x00\x11\x00\x00\x00\x00\x00\x00!U\x80\xa8\x88\x82\x80\x01\x00\x00\x00\x00\x00\x00H@\x11\xaa\xc0\x82\x00 *\n\x00\x00\x00\x00\x00\x00\x00\x00\n\xabb@ \x04\x00! \x84\x00\x00\x00\x00\x02@\xa5\x15A$\x04\x81(\n\x00\x00\x00\x00\x00\x00 \x01\x10\x02\xe0\x91\x02\x00\x00\x04\x00\x00\x00\x00\x00\x00\x01 \xa9\tQH@\x91 P\x00\x00\x00\x00\x00\x00\x08\x00\x00\xa0T\xa5\x00@\x80\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"\x00\x00\x00\x00\xa2\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00 T\xa0\t\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00@\x02\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00*\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x10\x00\x00\x10\x02\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00@\x04\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x08@\x10\x00\x00\x00\x00'

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES)
            device.apply_settings(self.client, homescreen=img)

    @pytest.mark.skip_t2
    def test_apply_auto_lock_delay(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES_PIN)
            device.apply_settings(self.client, auto_lock_delay_ms=int(10e3))  # 10 secs

        time.sleep(0.1)  # sleep less than auto-lock delay
        with self.client:
            # No PIN protection is required.
            self.client.set_expected_responses([proto.Success()])
            self.client.ping(msg="", pin_protection=True)

        time.sleep(10.1)  # sleep more than auto-lock delay
        with self.client:
            self.client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.Success()]
            )
            self.client.ping(msg="", pin_protection=True)

    @pytest.mark.skip_t2
    def test_apply_minimal_auto_lock_delay(self):
        """
        Verify that the delay is not below the minimal auto-lock delay (10 secs)
        otherwise the device may auto-lock before any user interaction.
        """
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses(EXPECTED_RESPONSES_PIN)
            # Note: the actual delay will be 10 secs (see above).
            device.apply_settings(self.client, auto_lock_delay_ms=int(1e3))

        time.sleep(0.1)  # sleep less than auto-lock delay
        with self.client:
            # No PIN protection is required.
            self.client.set_expected_responses([proto.Success()])
            self.client.ping(msg="", pin_protection=True)

        time.sleep(2)  # sleep less than the minimal auto-lock delay
        with self.client:
            # No PIN protection is required.
            self.client.set_expected_responses([proto.Success()])
            self.client.ping(msg="", pin_protection=True)

        time.sleep(10.1)  # sleep more than the minimal auto-lock delay
        with self.client:
            self.client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.Success()]
            )
            self.client.ping(msg="", pin_protection=True)
