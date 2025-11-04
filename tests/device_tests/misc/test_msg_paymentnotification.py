# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from trezorlib import btc, misc
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path


@pytest.mark.experimental
@pytest.mark.models("core")
def test_paymentnotification(session: Session):
    from ..payment_req import CoinPurchaseMemo, TextMemo, make_payment_request

    purchase_memo = CoinPurchaseMemo(
        amount="0.0636 BTC",
        coin_name="Bitcoin",
        slip44=0,
        address_n=parse_path("m/44h/0h/0h/0/0"),
    )
    purchase_memo.address_resp = btc.get_authenticated_address(
        session, purchase_memo.coin_name, purchase_memo.address_n
    )

    text_memo = TextMemo("We will deduct 1234.56 USD from your account")

    nonce = misc.get_nonce(session)
    payment_request = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=None,
        outputs=None,
        memos=[purchase_memo, text_memo],
        nonce=nonce,
        amount_size_bytes=8,
    )

    misc.payment_notification(session, payment_request)
