# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

"""Restricted xpub export shows a warning, regardless of safety checks:
paths shorter than 2 levels and SLIP-15, SLIP-16 and BIP-85 subtrees, except
for depth-1 nodes used by third parties. Hardening is ignored."""

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import Cancelled
from trezorlib.tools import parse_path

from ...common import MOCK_GET_ENTROPY, is_core
from ...input_flows import InputFlowConfirmAllWarnings
from ...input_flows_helpers import BackupFlow

# The classification of individual paths is covered by
# test_is_xpub_export_restricted in core/tests/test_apps.common.paths.py. These
# tests only cover the wiring in the handlers and the confirmation flow.


def test_allowed(session: Session):
    with session.test_ctx as client:
        client.set_expected_responses([messages.PublicKey])
        res = btc.get_public_node(session, parse_path("m/0h"))
    assert res.xpub


_WARNING = messages.ButtonRequest(code=messages.ButtonRequestType.UnknownDerivationPath)


def _confirm_warnings(session: Session, client: TrezorTestContext) -> None:
    if is_core(session):
        IF = InputFlowConfirmAllWarnings(session)
        client.set_input_flow(IF.get())


def _get_confirmed(session: Session, path: str) -> messages.PublicKey:
    with session.test_ctx as client:
        _confirm_warnings(session, client)
        client.set_expected_responses([_WARNING, messages.PublicKey])
        return btc.get_public_node(session, parse_path(path))


def test_restricted_confirmed(session: Session):
    res = _get_confirmed(session, "m/10016h/0")
    assert res.xpub


def test_restricted_rejected(session: Session):
    with session.test_ctx as client, pytest.raises(Cancelled):
        client.set_expected_responses(
            [_WARNING, messages.Failure(code=messages.FailureType.ActionCancelled)]
        )

        def input_flow():
            yield
            session.debug.press_no()

        client.set_input_flow(input_flow())
        btc.get_public_node(session, parse_path("m"))


@pytest.mark.setup_client(uninitialized=True)
def test_entropy_check_restricted(session: Session):
    # Restricted xpubs show the warning during the entropy check too. Rejecting
    # it aborts the whole reset on core and fails the request on legacy.
    with session.test_ctx as client:

        def input_flow():
            if is_core(session):
                yield from BackupFlow(client).confirm_new_wallet()
            while True:
                br = yield
                if br.code == messages.ButtonRequestType.UnknownDerivationPath:
                    session.debug.press_no()
                    return
                session.debug.press_yes()

        client.set_input_flow(input_flow())
        with pytest.raises(Cancelled):
            device.setup(
                session,
                strength=128,
                entropy_check_count=1,
                paths=[parse_path("m/84h")],
                backup_type=messages.BackupType.Bip39,
                skip_backup=True,
                pin_protection=False,
                passphrase_protection=False,
                _get_entropy=MOCK_GET_ENTROPY,
            )
    session.refresh_features()
    assert session.features.initialized is False
