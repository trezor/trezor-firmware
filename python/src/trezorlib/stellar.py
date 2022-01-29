# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from decimal import Decimal
from typing import TYPE_CHECKING, List, Tuple, Union

from . import exceptions, messages
from .tools import expect

if TYPE_CHECKING:
    from .protobuf import MessageType
    from .client import TrezorClient
    from .tools import Address

    StellarMessageType = Union[
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
    ]

try:
    from stellar_sdk import (
        AccountMerge,
        AllowTrust,
        Asset,
        BumpSequence,
        ChangeTrust,
        CreateAccount,
        CreatePassiveSellOffer,
        HashMemo,
        IdMemo,
        ManageData,
        ManageSellOffer,
        NoneMemo,
        Operation,
        PathPaymentStrictReceive,
        PathPaymentStrictSend,
        Payment,
        ReturnHashMemo,
        SetOptions,
        TextMemo,
        TransactionEnvelope,
        TrustLineEntryFlag,
        Price,
        Network,
        ManageBuyOffer,
        MuxedAccount,
    )
    from stellar_sdk.xdr.signer_key_type import SignerKeyType

    HAVE_STELLAR_SDK = True
    DEFAULT_NETWORK_PASSPHRASE = Network.PUBLIC_NETWORK_PASSPHRASE

except ImportError:
    HAVE_STELLAR_SDK = False
    DEFAULT_NETWORK_PASSPHRASE = "Public Global Stellar Network ; September 2015"

DEFAULT_BIP32_PATH = "m/44h/148h/0h"


def from_envelope(
    envelope: "TransactionEnvelope",
) -> Tuple[messages.StellarSignTx, List["StellarMessageType"]]:
    """Parses transaction envelope into a map with the following keys:
    tx - a StellarSignTx describing the transaction header
    operations - an array of protobuf message objects for each operation
    """
    if not HAVE_STELLAR_SDK:
        raise RuntimeError("Stellar SDK not available")

    parsed_tx = envelope.transaction
    if parsed_tx.time_bounds is None:
        raise ValueError("Timebounds are mandatory")

    memo_type = messages.StellarMemoType.NONE
    memo_text = None
    memo_id = None
    memo_hash = None
    if isinstance(parsed_tx.memo, NoneMemo):
        pass
    elif isinstance(parsed_tx.memo, TextMemo):
        # memo_text is specified as UTF-8 string, but returned as bytes from the XDR parser
        memo_type = messages.StellarMemoType.TEXT
        memo_text = parsed_tx.memo.memo_text.decode("utf-8")
    elif isinstance(parsed_tx.memo, IdMemo):
        memo_type = messages.StellarMemoType.ID
        memo_id = parsed_tx.memo.memo_id
    elif isinstance(parsed_tx.memo, HashMemo):
        memo_type = messages.StellarMemoType.HASH
        memo_hash = parsed_tx.memo.memo_hash
    elif isinstance(parsed_tx.memo, ReturnHashMemo):
        memo_type = messages.StellarMemoType.RETURN
        memo_hash = parsed_tx.memo.memo_return
    else:
        raise ValueError("Unsupported memo type")

    _raise_if_account_muxed_id_exists(parsed_tx.source)
    tx = messages.StellarSignTx(
        source_account=parsed_tx.source.account_id,
        fee=parsed_tx.fee,
        sequence_number=parsed_tx.sequence,
        timebounds_start=parsed_tx.time_bounds.min_time,
        timebounds_end=parsed_tx.time_bounds.max_time,
        memo_type=memo_type,
        memo_text=memo_text,
        memo_id=memo_id,
        memo_hash=memo_hash,
        num_operations=len(parsed_tx.operations),
        network_passphrase=envelope.network_passphrase,
    )

    operations = [_read_operation(op) for op in parsed_tx.operations]
    return tx, operations


def _read_operation(op: "Operation") -> "StellarMessageType":
    # TODO: Let's add muxed account support later.
    if op.source:
        _raise_if_account_muxed_id_exists(op.source)
        source_account = op.source.account_id
    else:
        source_account = None
    if isinstance(op, CreateAccount):
        return messages.StellarCreateAccountOp(
            source_account=source_account,
            new_account=op.destination,
            starting_balance=_read_amount(op.starting_balance),
        )
    if isinstance(op, Payment):
        _raise_if_account_muxed_id_exists(op.destination)
        return messages.StellarPaymentOp(
            source_account=source_account,
            destination_account=op.destination.account_id,
            asset=_read_asset(op.asset),
            amount=_read_amount(op.amount),
        )
    if isinstance(op, PathPaymentStrictReceive):
        _raise_if_account_muxed_id_exists(op.destination)
        return messages.StellarPathPaymentStrictReceiveOp(
            source_account=source_account,
            send_asset=_read_asset(op.send_asset),
            send_max=_read_amount(op.send_max),
            destination_account=op.destination.account_id,
            destination_asset=_read_asset(op.dest_asset),
            destination_amount=_read_amount(op.dest_amount),
            paths=[_read_asset(asset) for asset in op.path],
        )
    if isinstance(op, ManageSellOffer):
        price = _read_price(op.price)
        return messages.StellarManageSellOfferOp(
            source_account=source_account,
            selling_asset=_read_asset(op.selling),
            buying_asset=_read_asset(op.buying),
            amount=_read_amount(op.amount),
            price_n=price.n,
            price_d=price.d,
            offer_id=op.offer_id,
        )
    if isinstance(op, CreatePassiveSellOffer):
        price = _read_price(op.price)
        return messages.StellarCreatePassiveSellOfferOp(
            source_account=source_account,
            selling_asset=_read_asset(op.selling),
            buying_asset=_read_asset(op.buying),
            amount=_read_amount(op.amount),
            price_n=price.n,
            price_d=price.d,
        )
    if isinstance(op, SetOptions):
        operation = messages.StellarSetOptionsOp(
            source_account=source_account,
            inflation_destination_account=op.inflation_dest,
            clear_flags=op.clear_flags,
            set_flags=op.set_flags,
            master_weight=op.master_weight,
            low_threshold=op.low_threshold,
            medium_threshold=op.med_threshold,
            high_threshold=op.high_threshold,
            home_domain=op.home_domain,
        )
        if op.signer:
            signer_type = op.signer.signer_key.signer_key.type
            if signer_type == SignerKeyType.SIGNER_KEY_TYPE_ED25519:
                signer_key = op.signer.signer_key.signer_key.ed25519.uint256
            elif signer_type == SignerKeyType.SIGNER_KEY_TYPE_HASH_X:
                signer_key = op.signer.signer_key.signer_key.hash_x.uint256
            elif signer_type == SignerKeyType.SIGNER_KEY_TYPE_PRE_AUTH_TX:
                signer_key = op.signer.signer_key.signer_key.pre_auth_tx.uint256
            else:
                raise ValueError("Unsupported signer key type")
            operation.signer_type = messages.StellarSignerType(signer_type.value)
            operation.signer_key = signer_key
            operation.signer_weight = op.signer.weight
        return operation
    if isinstance(op, ChangeTrust):
        return messages.StellarChangeTrustOp(
            source_account=source_account,
            asset=_read_asset(op.asset),
            limit=_read_amount(op.limit),
        )
    if isinstance(op, AllowTrust):
        if op.authorize not in (
            TrustLineEntryFlag.UNAUTHORIZED_FLAG,
            TrustLineEntryFlag.AUTHORIZED_FLAG,
        ):
            raise ValueError("Unsupported trust line flag")
        asset_type = (
            messages.StellarAssetType.ALPHANUM4
            if len(op.asset_code) <= 4
            else messages.StellarAssetType.ALPHANUM12
        )
        return messages.StellarAllowTrustOp(
            source_account=source_account,
            trusted_account=op.trustor,
            asset_type=asset_type,
            asset_code=op.asset_code,
            is_authorized=bool(op.authorize.value),
        )
    if isinstance(op, AccountMerge):
        _raise_if_account_muxed_id_exists(op.destination)
        return messages.StellarAccountMergeOp(
            source_account=source_account,
            destination_account=op.destination.account_id,
        )
    # Inflation is not implemented since anyone can submit this operation to the network
    if isinstance(op, ManageData):
        return messages.StellarManageDataOp(
            source_account=source_account,
            key=op.data_name,
            value=op.data_value,
        )
    if isinstance(op, BumpSequence):
        return messages.StellarBumpSequenceOp(
            source_account=source_account, bump_to=op.bump_to
        )
    if isinstance(op, ManageBuyOffer):
        price = _read_price(op.price)
        return messages.StellarManageBuyOfferOp(
            source_account=source_account,
            selling_asset=_read_asset(op.selling),
            buying_asset=_read_asset(op.buying),
            amount=_read_amount(op.amount),
            price_n=price.n,
            price_d=price.d,
            offer_id=op.offer_id,
        )
    if isinstance(op, PathPaymentStrictSend):
        _raise_if_account_muxed_id_exists(op.destination)
        return messages.StellarPathPaymentStrictSendOp(
            source_account=source_account,
            send_asset=_read_asset(op.send_asset),
            send_amount=_read_amount(op.send_amount),
            destination_account=op.destination.account_id,
            destination_asset=_read_asset(op.dest_asset),
            destination_min=_read_amount(op.dest_min),
            paths=[_read_asset(asset) for asset in op.path],
        )
    raise ValueError(f"Unknown operation type: {op.__class__.__name__}")


def _raise_if_account_muxed_id_exists(account: "MuxedAccount"):
    # Currently Trezor firmware does not support MuxedAccount,
    # so we throw an exception here.
    if account.account_muxed_id is not None:
        raise ValueError("MuxedAccount is not supported")


def _read_amount(amount: str) -> int:
    return Operation.to_xdr_amount(amount)


def _read_price(price: Union["Price", str, Decimal]) -> "Price":
    # In the coming stellar-sdk 6.x, the type of price must be Price,
    # at that time we can remove this function
    if isinstance(price, Price):
        return price
    return Price.from_raw_price(price)


def _read_asset(asset: "Asset") -> messages.StellarAsset:
    """Reads a stellar Asset from unpacker"""
    if asset.is_native():
        return messages.StellarAsset(type=messages.StellarAssetType.NATIVE)
    if asset.guess_asset_type() == "credit_alphanum4":
        return messages.StellarAsset(
            type=messages.StellarAssetType.ALPHANUM4,
            code=asset.code,
            issuer=asset.issuer,
        )
    if asset.guess_asset_type() == "credit_alphanum12":
        return messages.StellarAsset(
            type=messages.StellarAssetType.ALPHANUM12,
            code=asset.code,
            issuer=asset.issuer,
        )
    raise ValueError("Unsupported asset type")


# ====== Client functions ====== #


@expect(messages.StellarAddress, field="address", ret_type=str)
def get_address(
    client: "TrezorClient", address_n: "Address", show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.StellarGetAddress(address_n=address_n, show_display=show_display)
    )


def sign_tx(
    client: "TrezorClient",
    tx: messages.StellarSignTx,
    operations: List["StellarMessageType"],
    address_n: "Address",
    network_passphrase: str = DEFAULT_NETWORK_PASSPHRASE,
) -> messages.StellarSignedTx:
    tx.network_passphrase = network_passphrase
    tx.address_n = address_n
    tx.num_operations = len(operations)
    # Signing loop works as follows:
    #
    # 1. Start with tx (header information for the transaction) and operations (an array of operation protobuf messagess)
    # 2. Send the tx header to the device
    # 3. Receive a StellarTxOpRequest message
    # 4. Send operations one by one until all operations have been sent. If there are more operations to sign, the device will send a StellarTxOpRequest message
    # 5. The final message received will be StellarSignedTx which is returned from this method
    resp = client.call(tx)
    try:
        while isinstance(resp, messages.StellarTxOpRequest):
            resp = client.call(operations.pop(0))
    except IndexError:
        # pop from empty list
        raise exceptions.TrezorException(
            "Reached end of operations without a signature."
        ) from None

    if not isinstance(resp, messages.StellarSignedTx):
        raise exceptions.TrezorException(
            f"Unexpected message: {resp.__class__.__name__}"
        )

    if operations:
        raise exceptions.TrezorException(
            "Received a signature before processing all operations."
        )

    return resp
