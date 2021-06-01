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

from trezorlib import MINIMUM_FIRMWARE_VERSION, btc, device, mapping, messages, protobuf
from trezorlib.tools import parse_path

from ..emulators import EmulatorWrapper
from . import for_all

SOURCE_ASK = 0
SOURCE_DEVICE = 1
SOURCE_HOST = 2


class ApplySettingsCompat(protobuf.MessageType):
    MESSAGE_WIRE_TYPE = 25

    FIELDS = {
        3: protobuf.Field("use_passphrase", "bool"),
        5: protobuf.Field("passphrase_source", "uint32"),
    }


mapping.map_class_to_type[ApplySettingsCompat] = ApplySettingsCompat.MESSAGE_WIRE_TYPE


@pytest.fixture
def emulator(gen, tag):
    with EmulatorWrapper(gen, tag) as emu:
        # set up a passphrase-protected device
        device.reset(
            emu.client,
            pin_protection=False,
            skip_backup=True,
        )
        resp = emu.client.call(
            ApplySettingsCompat(use_passphrase=True, passphrase_source=SOURCE_HOST)
        )
        assert isinstance(resp, messages.Success)

        yield emu


@for_all(
    core_minimum_version=MINIMUM_FIRMWARE_VERSION["T"],
    legacy_minimum_version=MINIMUM_FIRMWARE_VERSION["1"],
)
def test_passphrase_works(emulator):
    """Check that passphrase handling in trezorlib works correctly in all versions."""
    if emulator.client.features.model == "T" and emulator.client.version < (2, 3, 0):
        expected_responses = [
            messages.PassphraseRequest,
            messages.Deprecated_PassphraseStateRequest,
            messages.Address,
        ]
    elif (
        emulator.client.features.model == "T" and emulator.client.version < (2, 3, 3)
    ) or (
        emulator.client.features.model == "1" and emulator.client.version < (1, 9, 3)
    ):
        expected_responses = [
            messages.PassphraseRequest,
            messages.Address,
        ]
    else:
        expected_responses = [
            messages.PassphraseRequest,
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.Address,
        ]

    with emulator.client:
        emulator.client.use_passphrase("TREZOR")
        emulator.client.set_expected_responses(expected_responses)
        btc.get_address(emulator.client, "Testnet", parse_path("44h/1h/0h/0/0"))


@for_all(
    core_minimum_version=MINIMUM_FIRMWARE_VERSION["T"],
    legacy_minimum_version=(1, 9, 0),
)
def test_init_device(emulator):
    """Check that passphrase caching and session_id retaining works correctly across
    supported versions.
    """
    if emulator.client.features.model == "T" and emulator.client.version < (2, 3, 0):
        expected_responses = [
            messages.PassphraseRequest,
            messages.Deprecated_PassphraseStateRequest,
            messages.Address,
            messages.Features,
            messages.Address,
        ]
    elif (
        emulator.client.features.model == "T" and emulator.client.version < (2, 3, 3)
    ) or (
        emulator.client.features.model == "1" and emulator.client.version < (1, 9, 3)
    ):
        expected_responses = [
            messages.PassphraseRequest,
            messages.Address,
            messages.Features,
            messages.Address,
        ]
    else:
        expected_responses = [
            messages.PassphraseRequest,
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.Address,
            messages.Features,
            messages.Address,
        ]

    with emulator.client:
        emulator.client.use_passphrase("TREZOR")
        emulator.client.set_expected_responses(expected_responses)

        btc.get_address(emulator.client, "Testnet", parse_path("44h/1h/0h/0/0"))
        # in TT < 2.3.0 session_id will only be available after PassphraseStateRequest
        session_id = emulator.client.session_id
        emulator.client.init_device()
        btc.get_address(emulator.client, "Testnet", parse_path("44h/1h/0h/0/0"))
        assert session_id == emulator.client.session_id
