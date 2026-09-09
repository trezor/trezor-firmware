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

from __future__ import annotations

import typing as t

from . import exceptions, messages
from .tools import workflow

if t.TYPE_CHECKING:
    from .client import Session
    from .tools import Address

    StellarMessageType = t.Union[
        messages.StellarAccountMergeOp,
        messages.StellarAllowTrustOp,
        messages.StellarBumpSequenceOp,
        messages.StellarChangeTrustOp,
        messages.StellarCreateAccountOp,
        messages.StellarCreatePassiveSellOfferOp,
        messages.StellarManageDataOp,
        messages.StellarManageBuyOfferOp,
        messages.StellarManageSellOfferOp,
        messages.StellarPathPaymentStrictReceiveOp,
        messages.StellarPathPaymentStrictSendOp,
        messages.StellarPaymentOp,
        messages.StellarSetOptionsOp,
        messages.StellarClaimClaimableBalanceOp,
        messages.StellarInvokeHostFunctionOp,
    ]

DEFAULT_BIP32_PATH = "m/44h/148h/0h"
DEFAULT_NETWORK_PASSPHRASE = "Public Global Stellar Network ; September 2015"


# ====== Client functions ====== #


def get_address(*args: t.Any, **kwargs: t.Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


@workflow(capability=messages.Capability.Stellar)
def get_authenticated_address(
    session: Session,
    address_n: Address,
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.StellarAddress:
    return session.call(
        messages.StellarGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.StellarAddress,
    )


@workflow(capability=messages.Capability.Stellar)
def sign_tx(
    session: Session,
    tx: messages.StellarSignTx,
    operations: list[StellarMessageType],
    tx_ext: messages.StellarTxExt,
    address_n: Address,
    network_passphrase: str = DEFAULT_NETWORK_PASSPHRASE,
) -> messages.StellarSignedTx:
    tx.network_passphrase = network_passphrase
    tx.address_n = address_n
    tx.num_operations = len(operations)
    # Signing loop works as follows:
    #
    # 1. Start with tx (header information for the transaction) and operations (an array of operation protobuf messages)
    # 2. Send the tx header to the device
    # 3. Receive a StellarTxOpRequest message
    # 4. Send operations one by one until all operations have been sent. If there are more operations to sign, the device will send a StellarTxOpRequest message
    # 5. If the transaction contains Soroban operations, the device will send a StellarTxExtRequest message. Send tx_ext to the device.
    # 6. The final message received will be StellarSignedTx which is returned from this method
    resp = session.call(tx)
    try:
        while isinstance(resp, messages.StellarTxOpRequest):
            resp = session.call(operations.pop(0))
    except IndexError:
        # pop from empty list
        raise exceptions.TrezorException(
            "Reached end of operations without a signature."
        ) from None

    # Handle StellarTxExtRequest for Soroban transactions
    if isinstance(resp, messages.StellarTxExtRequest):
        resp = session.call(tx_ext)

    resp = messages.StellarSignedTx.ensure_isinstance(resp)

    if operations:
        raise exceptions.TrezorException(
            "Received a signature before processing all operations."
        )

    return resp


@workflow(capability=messages.Capability.Stellar)
def sign_soroban_authorization(
    session: Session,
    address_n: Address,
    network_passphrase: str,
    authorization: messages.StellarSorobanAuthorizationWithAddress,
) -> messages.StellarSorobanAuthorizationSignature:
    """Sign a Soroban authorization on the device."""
    return session.call(
        messages.StellarSignSorobanAuthorization(
            address_n=address_n,
            network_passphrase=network_passphrase,
            envelope_type=messages.StellarSorobanAuthorizationEnvelopeType.ENVELOPE_TYPE_SOROBAN_AUTHORIZATION_WITH_ADDRESS,
            soroban_authorization_with_address=authorization,
        ),
        expect=messages.StellarSorobanAuthorizationSignature,
    )
