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

from typing import Iterator

import pytest

from trezorlib import btc, device, mapping, messages, models, protobuf
from trezorlib._internal.emulator import Emulator
from trezorlib.client import ProtocolVersion
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path
from trezorlib.transport.session import SessionV1

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


mapping.DEFAULT_MAPPING.register(ApplySettingsCompat)


@pytest.fixture
def emulator(gen: str, tag: str) -> Iterator[Emulator]:
    with EmulatorWrapper(gen, tag) as emu:
        # set up a passphrase-protected device
        device.setup(
            emu.client.get_seedless_session(),
            pin_protection=False,
            skip_backup=True,
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
        )
        emu.client.invalidate()
        resp = emu.client.get_seedless_session().call(
            ApplySettingsCompat(use_passphrase=True, passphrase_source=SOURCE_HOST)
        )
        assert isinstance(resp, messages.Success)

        yield emu


@for_all(
    core_minimum_version=models.TREZOR_T.minimum_version,
    legacy_minimum_version=models.TREZOR_ONE.minimum_version,
)
def test_passphrase_works(emulator: Emulator):
    """Check that passphrase handling in trezorlib works correctly in all versions."""
    protocol_v1 = emulator.client.protocol_version == ProtocolVersion.V1
    if (
        emulator.client.features.model == "T" and emulator.client.version < (2, 3, 3)
    ) or (
        emulator.client.features.model == "1" and emulator.client.version < (1, 9, 3)
    ):
        expected_responses = [
            (protocol_v1, messages.Features),
            messages.PassphraseRequest,
            messages.Address,
        ]
    else:
        expected_responses = [
            (protocol_v1, messages.Features),
            messages.PassphraseRequest,
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.Address,
        ]
    with emulator.client as client:
        client.set_expected_responses(expected_responses)
        if protocol_v1:
            session = Session(SessionV1.new(emulator.client))
            resp = session.call_raw(
                messages.GetAddress(
                    address_n=parse_path("44h/1h/0h/0/0"),
                    coin_name="Testnet",
                )
            )
            if isinstance(resp, messages.PassphraseRequest):
                resp = session.call_raw(messages.PassphraseAck(passphrase="TREZOR"))
            if isinstance(resp, messages.ButtonRequest):
                resp = session._callback_button(resp)
            if isinstance(resp, messages.ButtonRequest):
                resp = session._callback_button(resp)
        else:
            session = client.get_session(passphrase="TREZOR")
            btc.get_address(session, "Testnet", parse_path("44h/1h/0h/0/0"))


@for_all(
    core_minimum_version=models.TREZOR_T.minimum_version,
    legacy_minimum_version=(1, 9, 0),
)
def test_init_device(emulator: Emulator):
    """Check that passphrase caching and session_id retaining works correctly across
    supported versions.
    """
    protocol_v1 = emulator.client.protocol_version == ProtocolVersion.V1
    if (
        emulator.client.features.model == "T" and emulator.client.version < (2, 3, 3)
    ) or (
        emulator.client.features.model == "1" and emulator.client.version < (1, 9, 3)
    ):
        expected_responses = [
            (protocol_v1, messages.Features),
            messages.PassphraseRequest,
            messages.Address,
            messages.Features,
            messages.Address,
        ]
    else:
        expected_responses = [
            (protocol_v1, messages.Features),
            messages.PassphraseRequest,
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.Address,
            messages.Features,
            messages.Address,
        ]

    with emulator.client as client:
        client.set_expected_responses(expected_responses)
        if protocol_v1:
            session = Session(SessionV1.new(emulator.client))
            resp = session.call_raw(
                messages.GetAddress(
                    address_n=parse_path("44h/1h/0h/0/0"),
                    coin_name="Testnet",
                )
            )
            if isinstance(resp, messages.PassphraseRequest):
                resp = session.call_raw(messages.PassphraseAck(passphrase="TREZOR"))
            if isinstance(resp, messages.ButtonRequest):
                resp = session._callback_button(resp)
            if isinstance(resp, messages.ButtonRequest):
                resp = session._callback_button(resp)

        else:
            session = client.get_session(passphrase="TREZOR")
            btc.get_address(session, "Testnet", parse_path("44h/1h/0h/0/0"))
        # in TT < 2.3.0 session_id will only be available after PassphraseStateRequest
        # support for TT < 2.3.0 dropped in trezorlib 0.14
        session_id = session.id
        if protocol_v1:
            session.call(messages.Initialize(session_id=session_id))
        btc.get_address(
            session,
            "Testnet",
            parse_path("44h/1h/0h/0/0"),
        )
        assert session_id == session.id
