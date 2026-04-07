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

from typing import TYPE_CHECKING, Any, List, Optional

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session


@workflow(capability=messages.Capability.Solana)
def get_public_key(
    session: "Session",
    address_n: List[int],
    show_display: bool,
) -> bytes:
    return session.call(
        messages.SolanaGetPublicKey(address_n=address_n, show_display=show_display),
        expect=messages.SolanaPublicKey,
    ).public_key


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


@workflow(capability=messages.Capability.Solana)
def get_authenticated_address(
    session: "Session",
    address_n: List[int],
    show_display: bool,
    chunkify: bool = False,
) -> messages.SolanaAddress:
    return session.call(
        messages.SolanaGetAddress(
            address_n=address_n,
            show_display=show_display,
            chunkify=chunkify,
        ),
        expect=messages.SolanaAddress,
    )


@workflow(capability=messages.Capability.Solana)
def sign_tx(
    session: "Session",
    address_n: List[int],
    serialized_tx: bytes,
    additional_info: Optional[messages.SolanaTxAdditionalInfo],
    payment_req: Optional[messages.PaymentRequest] = None,
) -> bytes:
    return session.call(
        messages.SolanaSignTx(
            address_n=address_n,
            serialized_tx=serialized_tx,
            additional_info=additional_info,
            payment_req=payment_req,
        ),
        expect=messages.SolanaTxSignature,
    ).signature
