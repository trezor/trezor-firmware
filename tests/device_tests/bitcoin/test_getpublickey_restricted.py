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

"""Restricted xpub export: paths shorter than 3 levels and SLIP-15, SLIP-16 and
BIP-85 subtrees, except for the m/0', m/45' and m/4541509'/1112098098'
subtrees."""

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
    pytest.param("m/1", id="depth1_unhardened"),
    pytest.param("m/44h", id="purpose"),
    pytest.param("m/84h/0h", id="coin_type"),
    pytest.param("m/1/1h", id="depth2_mixed"),
    pytest.param("m/10015h/0h", id="slip15"),
    pytest.param("m/10016h/0", id="slip16"),
    pytest.param("m/10016h/0/1/2/3", id="slip16_deep"),
    pytest.param("m/83696968h/2h/0h", id="bip85_wif"),
)

ALLOWED = (
    pytest.param("m/0h", id="root_fingerprint"),
    pytest.param("m/0h/1", id="root_fingerprint_child"),
    pytest.param("m/45h", id="casa"),
    pytest.param("m/45h/0", id="bip45_cosigner"),
    pytest.param("m/4541509h/1112098098h", id="electrum_storage"),
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


@pytest.mark.parametrize("path", RESTRICTED)
def test_restricted_confirmed(session: Session, path: str):
    _relax_safety_checks(session)
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
        res = btc.get_public_node(session, parse_path(path))
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


def _get_confirmed(session: Session, path: str) -> None:
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
        btc.get_public_node(session, parse_path(path))


def _get_unconfirmed(session: Session, path: str) -> None:
    with session.test_ctx as client:
        client.set_expected_responses([messages.PublicKey])
        btc.get_public_node(session, parse_path(path))


def test_restricted_confirmed_root_subtree(session: Session):
    # Blockstream GDK exports the root xpub and then several restricted xpubs
    # below it. Once the root is confirmed, its subtree is not confirmed again.
    _relax_safety_checks(session)
    _get_confirmed(session, "m")
    for path in (
        "m",
        "m/1885434739h",
        "m/18241h",
        "m/1195487518",
        "m/1",
        "m/3h/1h",
        "m/10016h/0",
    ):
        _get_unconfirmed(session, path)


def test_restricted_confirmed_subtree(session: Session):
    _relax_safety_checks(session)
    _get_confirmed(session, "m/1")
    _get_unconfirmed(session, "m/1")
    _get_unconfirmed(session, "m/1/2")
    _get_confirmed(session, "m/2")
    _get_unconfirmed(session, "m/2/1")


def test_restricted_confirmed_strict(session: Session):
    # Re-enabling safety checks forbids previously confirmed subtrees.
    _relax_safety_checks(session)
    _get_confirmed(session, "m")
    device.apply_settings(session, safety_checks=messages.SafetyCheckLevel.Strict)
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(session, parse_path("m/1"))


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
                paths=[parse_path("m/44h")],
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
@pytest.mark.parametrize("path", ("m/44h", "m/44h/60h"))
def test_ethereum_restricted(session: Session, path: str):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ethereum.get_public_node(session, parse_path(path))


@pytest.mark.altcoin
@pytest.mark.models("core")
def test_cardano_restricted(session: Session):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        cardano.get_public_key(
            session,
            parse_path("m/1852h/1815h"),
            derivation_type=messages.CardanoDerivationType.LEDGER,
        )
