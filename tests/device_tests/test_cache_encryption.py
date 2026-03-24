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

from trezorlib import btc, cardano
from trezorlib.debuglink import DebugSession as Session
from trezorlib.messages import CardanoDerivationType
from trezorlib.tools import parse_path

PIN4 = "1234"

BTC_PATH = parse_path("m/44h/0h/0h")
ETH_PATH = parse_path("m/44h/60h/0h")
CARDANO_PATH = parse_path("m/44h/1815h/0h")


pytestmark = pytest.mark.setup_client(pin=PIN4)


def test_session_persists_after_lock_unlock(session: Session):
    session_id = session.id

    btc_xpub_before = btc.get_public_node(session, BTC_PATH).xpub

    session.lock()

    with session.test_ctx:
        session.test_ctx.use_pin_sequence([PIN4])
        session.ensure_unlocked()

    assert session.id == session_id
    assert btc.get_public_node(session, BTC_PATH).xpub == btc_xpub_before


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.models("core")
@pytest.mark.parametrize("derivation_type", CardanoDerivationType)
def test_cardano_session_persists_after_lock_unlock(
    session: Session, derivation_type: CardanoDerivationType
):
    session_id = session.id

    cardano_pubkey_before = cardano.get_public_key(
        session, CARDANO_PATH, derivation_type=derivation_type
    ).xpub

    session.lock()

    with session.test_ctx:
        session.test_ctx.use_pin_sequence([PIN4])
        session.ensure_unlocked()

    assert session.id == session_id
    assert (
        cardano.get_public_key(
            session, CARDANO_PATH, derivation_type=derivation_type
        ).xpub
        == cardano_pubkey_before
    )
