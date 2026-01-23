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

from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Tuple, Union

from . import exceptions, messages

if TYPE_CHECKING:
    from .tools import Address
    from .transport.session import Session

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
        messages.StellarClaimClaimableBalanceOp,
        messages.StellarInvokeHostFunctionOp,
    ]

try:
    from stellar_sdk import AccountMerge
    from stellar_sdk import Address as StellarAddress
    from stellar_sdk import (
        AllowTrust,
        Asset,
        BumpSequence,
        ChangeTrust,
        ClaimClaimableBalance,
        CreateAccount,
        CreatePassiveSellOffer,
        HashMemo,
        IdMemo,
        InvokeHostFunction,
        LiquidityPoolAsset,
        ManageBuyOffer,
        ManageData,
        ManageSellOffer,
        MuxedAccount,
        Network,
        NoneMemo,
        Operation,
        PathPaymentStrictReceive,
        PathPaymentStrictSend,
        Payment,
        Price,
        ReturnHashMemo,
        SetOptions,
        TextMemo,
        TransactionEnvelope,
        TrustLineEntryFlag,
        xdr,
    )
    from stellar_sdk.address import AddressType

    HAVE_STELLAR_SDK = True
    DEFAULT_NETWORK_PASSPHRASE = Network.PUBLIC_NETWORK_PASSPHRASE

except ImportError:
    HAVE_STELLAR_SDK = False
    DEFAULT_NETWORK_PASSPHRASE = "Public Global Stellar Network ; September 2015"

DEFAULT_BIP32_PATH = "m/44h/148h/0h"


def from_envelope(
    envelope: "TransactionEnvelope",
) -> Tuple[messages.StellarSignTx, List["StellarMessageType"], messages.StellarTxExt]:
    """Parses transaction envelope into a map with the following keys:
    tx - a StellarSignTx describing the transaction header
    operations - an array of protobuf message objects for each operation
    """
    if not HAVE_STELLAR_SDK:
        raise RuntimeError("Stellar SDK not available")

    parsed_tx = envelope.transaction
    if parsed_tx.preconditions is None or parsed_tx.preconditions.time_bounds is None:
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
        timebounds_start=parsed_tx.preconditions.time_bounds.min_time,
        timebounds_end=parsed_tx.preconditions.time_bounds.max_time,
        memo_type=memo_type,
        memo_text=memo_text,
        memo_id=memo_id,
        memo_hash=memo_hash,
        num_operations=len(parsed_tx.operations),
        network_passphrase=envelope.network_passphrase,
    )

    operations = [_read_operation(op) for op in parsed_tx.operations]

    if parsed_tx.soroban_data:
        tx_ext = messages.StellarTxExt(
            v=1,
            soroban_data=parsed_tx.soroban_data.to_xdr_bytes(),
        )
    else:
        tx_ext = messages.StellarTxExt(v=0)

    return tx, operations, tx_ext


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
            signer_type = op.signer.signer_key.signer_key_type
            operation.signer_type = messages.StellarSignerType(signer_type.value)
            operation.signer_key = op.signer.signer_key.signer_key
            operation.signer_weight = op.signer.weight
        return operation
    if isinstance(op, ChangeTrust):
        if isinstance(op.asset, LiquidityPoolAsset):
            raise ValueError("Liquidity pool assets are not supported")
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
    if isinstance(op, ClaimClaimableBalance):
        return messages.StellarClaimClaimableBalanceOp(
            source_account=source_account,
            balance_id=bytes.fromhex(op.balance_id),
        )
    if isinstance(op, InvokeHostFunction):
        return messages.StellarInvokeHostFunctionOp(
            source_account=source_account,
            function=_read_host_function(op.host_function),
            auth=[_read_authorization_entry(entry) for entry in op.auth],
        )
    raise ValueError(f"Unknown operation type: {op.__class__.__name__}")


def _raise_if_account_muxed_id_exists(account: "MuxedAccount") -> None:
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


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.StellarAddress:
    return session.call(
        messages.StellarGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.StellarAddress,
    )


def sign_tx(
    session: "Session",
    tx: messages.StellarSignTx,
    operations: List["StellarMessageType"],
    tx_ext: messages.StellarTxExt,
    address_n: "Address",
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


def _read_sc_address(address: "xdr.SCAddress") -> messages.StellarSCAddress:
    """Read an SCAddress from XDR."""
    addr = StellarAddress.from_xdr_sc_address(address)
    if addr.type == AddressType.ACCOUNT:
        address_type = messages.StellarSCAddressType.SC_ADDRESS_TYPE_ACCOUNT
    elif addr.type == AddressType.CONTRACT:
        address_type = messages.StellarSCAddressType.SC_ADDRESS_TYPE_CONTRACT
    elif addr.type == AddressType.MUXED_ACCOUNT:
        address_type = messages.StellarSCAddressType.SC_ADDRESS_TYPE_MUXED_ACCOUNT
    elif addr.type == AddressType.CLAIMABLE_BALANCE:
        address_type = messages.StellarSCAddressType.SC_ADDRESS_TYPE_CLAIMABLE_BALANCE
    elif addr.type == AddressType.LIQUIDITY_POOL:
        address_type = messages.StellarSCAddressType.SC_ADDRESS_TYPE_LIQUIDITY_POOL
    else:
        raise ValueError(f"Unsupported address type: {addr.type}")
    return messages.StellarSCAddress(type=address_type, address=addr.key)


def _read_sc_val(val: "xdr.SCVal") -> messages.StellarSCVal:
    """Read an SCVal from XDR."""
    if val.type == xdr.SCValType.SCV_BOOL:
        return messages.StellarSCVal(type=messages.StellarSCValType.SCV_BOOL, b=val.b)
    elif val.type == xdr.SCValType.SCV_VOID:
        return messages.StellarSCVal(type=messages.StellarSCValType.SCV_VOID)
    elif val.type == xdr.SCValType.SCV_U32:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_U32, u32=val.u32.uint32
        )
    elif val.type == xdr.SCValType.SCV_I32:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_I32, i32=val.i32.int32
        )
    elif val.type == xdr.SCValType.SCV_U64:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_U64, u64=val.u64.uint64
        )
    elif val.type == xdr.SCValType.SCV_I64:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_I64, i64=val.i64.int64
        )
    elif val.type == xdr.SCValType.SCV_TIMEPOINT:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_TIMEPOINT,
            timepoint=val.timepoint.time_point.uint64,
        )
    elif val.type == xdr.SCValType.SCV_DURATION:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_DURATION,
            duration=val.duration.duration.uint64,
        )
    elif val.type == xdr.SCValType.SCV_U128:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_U128,
            u128=messages.StellarUInt128Parts(
                hi=val.u128.hi.uint64, lo=val.u128.lo.uint64
            ),
        )
    elif val.type == xdr.SCValType.SCV_I128:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_I128,
            i128=messages.StellarInt128Parts(
                hi=val.i128.hi.int64, lo=val.i128.lo.uint64
            ),
        )
    elif val.type == xdr.SCValType.SCV_U256:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_U256,
            u256=messages.StellarUInt256Parts(
                hi_hi=val.u256.hi_hi.uint64,
                hi_lo=val.u256.hi_lo.uint64,
                lo_hi=val.u256.lo_hi.uint64,
                lo_lo=val.u256.lo_lo.uint64,
            ),
        )
    elif val.type == xdr.SCValType.SCV_I256:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_I256,
            i256=messages.StellarInt256Parts(
                hi_hi=val.i256.hi_hi.int64,
                hi_lo=val.i256.hi_lo.uint64,
                lo_hi=val.i256.lo_hi.uint64,
                lo_lo=val.i256.lo_lo.uint64,
            ),
        )
    elif val.type == xdr.SCValType.SCV_BYTES:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_BYTES, bytes=val.bytes.sc_bytes
        )
    elif val.type == xdr.SCValType.SCV_STRING:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_STRING,
            string=val.str.sc_string,  # raw bytes, not necessarily UTF-8
        )
    elif val.type == xdr.SCValType.SCV_SYMBOL:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_SYMBOL,
            symbol=val.sym.sc_symbol.decode("utf-8"),
        )
    elif val.type == xdr.SCValType.SCV_VEC:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_VEC,
            vec=[_read_sc_val(v) for v in val.vec.sc_vec],
        )
    elif val.type == xdr.SCValType.SCV_MAP:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_MAP,
            map=[
                messages.StellarSCValMapEntry(
                    key=_read_sc_val(item.key), value=_read_sc_val(item.val)
                )
                for item in val.map.sc_map
            ],
        )
    elif val.type == xdr.SCValType.SCV_ADDRESS:
        return messages.StellarSCVal(
            type=messages.StellarSCValType.SCV_ADDRESS,
            address=_read_sc_address(val.address),
        )
    else:
        raise ValueError(f"Unsupported SCVal type: {val.type}")


def _read_invoke_contract_args(
    data: "xdr.InvokeContractArgs",
) -> messages.StellarInvokeContractArgs:
    """Read InvokeContractArgs from XDR."""
    return messages.StellarInvokeContractArgs(
        contract_address=_read_sc_address(data.contract_address),
        function_name=data.function_name.sc_symbol.decode("utf-8"),
        args=[_read_sc_val(arg) for arg in data.args],
    )


def _read_authorized_function(
    function: "xdr.SorobanAuthorizedFunction",
) -> messages.StellarSorobanAuthorizedFunction:
    """Read SorobanAuthorizedFunction from XDR."""
    if (
        function.type
        == xdr.SorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        return messages.StellarSorobanAuthorizedFunction(
            type=messages.StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN,
            contract_fn=_read_invoke_contract_args(function.contract_fn),
        )
    else:
        raise ValueError(f"Unsupported SorobanAuthorizedFunction type: {function.type}")


def _read_address_credentials(
    address_credentials: "xdr.SorobanAddressCredentials",
) -> messages.StellarSorobanAddressCredentials:
    """Read SorobanAddressCredentials from XDR."""
    return messages.StellarSorobanAddressCredentials(
        address=_read_sc_address(address_credentials.address),
        nonce=address_credentials.nonce.int64,
        signature_expiration_ledger=address_credentials.signature_expiration_ledger.uint32,
        signature=_read_sc_val(address_credentials.signature),
    )


def _read_credentials(
    credentials: "xdr.SorobanCredentials",
) -> messages.StellarSorobanCredentials:
    """Read SorobanCredentials from XDR."""
    if (
        credentials.type
        == xdr.SorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT
    ):
        return messages.StellarSorobanCredentials(
            type=messages.StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT
        )
    elif credentials.type == xdr.SorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS:
        return messages.StellarSorobanCredentials(
            type=messages.StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS,
            address=_read_address_credentials(credentials.address),
        )
    else:
        raise ValueError(f"Unsupported SorobanCredentials type: {credentials.type}")


def _read_authorized_invocation(
    invocation: "xdr.SorobanAuthorizedInvocation",
) -> messages.StellarSorobanAuthorizedInvocation:
    """Read SorobanAuthorizedInvocation from XDR."""
    return messages.StellarSorobanAuthorizedInvocation(
        function=_read_authorized_function(invocation.function),
        sub_invocations=[
            _read_authorized_invocation(sub) for sub in invocation.sub_invocations
        ],
    )


def _read_authorization_entry(
    entry: "xdr.SorobanAuthorizationEntry",
) -> messages.StellarSorobanAuthorizationEntry:
    """Read SorobanAuthorizationEntry from XDR."""
    return messages.StellarSorobanAuthorizationEntry(
        credentials=_read_credentials(entry.credentials),
        root_invocation=_read_authorized_invocation(entry.root_invocation),
    )


def _read_host_function(
    host_function: "xdr.HostFunction",
) -> messages.StellarHostFunction:
    """Read HostFunction from XDR."""
    if host_function.type != xdr.HostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        raise ValueError(f"Unsupported host function type: {host_function.type}")

    return messages.StellarHostFunction(
        type=messages.StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT,
        invoke_contract=_read_invoke_contract_args(host_function.invoke_contract),
    )
