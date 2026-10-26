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

"""Restricted xpub export: paths shorter than 2 levels and SLIP-15, SLIP-16 and
BIP-85 subtrees, except for depth-1 nodes used by third parties. Purposes are
matched regardless of hardening."""

import pytest

from trezorlib import btc, cardano, device, ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import MOCK_GET_ENTROPY, is_core
from ...input_flows import InputFlowConfirmAllWarnings
from ...input_flows_helpers import BackupFlow

RESTRICTED = (
    pytest.param("m", id="root"),
    pytest.param("m/2", id="depth1_unhardened"),
    pytest.param("m/84h", id="purpose"),
    pytest.param("m/10015h/0h", id="slip15"),
    pytest.param("m/10016h/0", id="slip16"),
    pytest.param("m/10016h/0/1/2/3", id="slip16_deep"),
    pytest.param("m/10016/0", id="slip16_unhardened"),
    pytest.param("m/83696968h/2h/0h", id="bip85_wif"),
)

ALLOWED = (
    pytest.param("m/0h", id="root_fingerprint"),
    pytest.param("m/0h/1", id="root_fingerprint_child"),
    pytest.param("m/45h", id="casa"),
    pytest.param("m/45", id="casa_unhardened"),
    pytest.param("m/1", id="green_multisig"),
    pytest.param("m/18241h", id="green_register"),
    pytest.param("m/1195487518", id="green_login"),
    pytest.param("m/1885434739h", id="green_client_secret"),
    pytest.param("m/44h", id="btcpay_vault"),
    pytest.param("m/48h", id="nunchuk_desktop"),
    pytest.param("m/45h/0", id="bip45_cosigner"),
    pytest.param("m/4541509h/1112098098h", id="electrum_storage"),
    pytest.param("m/84h/0h", id="coin_type"),
    pytest.param("m/1/1h", id="depth2_mixed"),
    pytest.param("m/84h/0h/0h", id="bip84_account"),
)


def _relax_safety_checks(session: Session) -> None:
    device.apply_settings(
        session, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )


@pytest.mark.parametrize("path", RESTRICTED)
@pytest.mark.parametrize("show_display", (False, True))
def test_restricted_forbidden(session: Session, path: str, show_display: bool):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(session, parse_path(path), show_display=show_display)


@pytest.mark.parametrize("path", ALLOWED)
def test_allowed(session: Session, path: str):
    res = btc.get_public_node(session, parse_path(path))
    assert res.xpub


def _get_confirmed(session: Session, path: str) -> messages.PublicKey:
    with session.test_ctx as client:
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session)
            client.set_input_flow(IF.get())
        client.set_expected_responses(
            [
                messages.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                messages.PublicKey,
            ]
        )
        return btc.get_public_node(session, parse_path(path))


@pytest.mark.parametrize("path", RESTRICTED)
def test_restricted_confirmed(session: Session, path: str):
    _relax_safety_checks(session)
    res = _get_confirmed(session, path)
    assert res.xpub


@pytest.mark.parametrize("path", RESTRICTED)
def test_restricted_rejected(session: Session, path: str):
    _relax_safety_checks(session)
    with session.test_ctx as client, pytest.raises(Cancelled):
        client.set_expected_responses(
            [
                messages.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                messages.Failure(code=messages.FailureType.ActionCancelled),
            ]
        )

        def input_flow():
            yield
            session.debug.press_no()

        client.set_input_flow(input_flow())
        btc.get_public_node(session, parse_path(path))


def test_restricted_confirmed_not_remembered(session: Session):
    # Every restricted xpub is confirmed, even if it was confirmed before or
    # lies below a confirmed one.
    _relax_safety_checks(session)
    _get_confirmed(session, "m")
    _get_confirmed(session, "m")
    _get_confirmed(session, "m/2")
    _get_confirmed(session, "m/10016h/0")


@pytest.mark.setup_client(uninitialized=True)
def test_entropy_check_restricted(session: Session):
    # Restricted xpubs are not exported during the entropy check either. Core
    # aborts the whole reset, legacy fails the request.
    with session.test_ctx as client:
        if is_core(session):
            client.set_input_flow(BackupFlow(client).confirm_new_wallet())
        with pytest.raises(TrezorFailure, match="Forbidden key path"):
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


@pytest.mark.altcoin
@pytest.mark.ethereum
@pytest.mark.parametrize("path", ("m", "m/60h"))
def test_ethereum_restricted(session: Session, path: str):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.get_public_node(session, parse_path(path))


@pytest.mark.altcoin
@pytest.mark.models("core")
def test_cardano_restricted(session: Session):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        cardano.get_public_key(
            session,
            parse_path("m/1852h"),
            derivation_type=messages.CardanoDerivationType.LEDGER,
        )
