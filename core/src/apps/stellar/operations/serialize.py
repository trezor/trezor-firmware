from typing import TYPE_CHECKING

from trezor.enums import StellarAssetType
from trezor.wire import DataError, ProcessError

from ..writers import (
    write_bool,
    write_bytes_fixed,
    write_int32,
    write_int64,
    write_pubkey,
    write_string,
    write_uint32,
    write_uint64,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import (
        StellarAccountMergeOp,
        StellarAllowTrustOp,
        StellarAsset,
        StellarBumpSequenceOp,
        StellarChangeTrustOp,
        StellarClaimClaimableBalanceOp,
        StellarCreateAccountOp,
        StellarCreatePassiveSellOfferOp,
        StellarHostFunction,
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeContractArgs,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSCAddress,
        StellarSCVal,
        StellarSetOptionsOp,
        StellarSorobanAddressCredentials,
        StellarSorobanAuthorizationEntry,
        StellarSorobanAuthorizedFunction,
        StellarSorobanAuthorizedInvocation,
        StellarSorobanCredentials,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )
    from trezor.utils import Writer


def write_account_merge_op(w: Writer, msg: StellarAccountMergeOp) -> None:
    write_pubkey(w, msg.destination_account)


def write_allow_trust_op(w: Writer, msg: StellarAllowTrustOp) -> None:
    # trustor account (the account being allowed to access the asset)
    write_pubkey(w, msg.trusted_account)
    write_uint32(w, msg.asset_type)
    _write_asset_code(w, msg.asset_type, msg.asset_code)

    write_bool(w, msg.is_authorized)


def write_bump_sequence_op(w: Writer, msg: StellarBumpSequenceOp) -> None:
    write_uint64(w, msg.bump_to)


def write_change_trust_op(w: Writer, msg: StellarChangeTrustOp) -> None:
    _write_asset(w, msg.asset)
    write_uint64(w, msg.limit)


def write_create_account_op(w: Writer, msg: StellarCreateAccountOp) -> None:
    write_pubkey(w, msg.new_account)
    write_uint64(w, msg.starting_balance)


def write_create_passive_sell_offer_op(
    w: Writer, msg: StellarCreatePassiveSellOfferOp
) -> None:
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    write_uint64(w, msg.amount)
    write_uint32(w, msg.price_n)
    write_uint32(w, msg.price_d)


def write_manage_data_op(w: Writer, msg: StellarManageDataOp) -> None:
    if len(msg.key) > 64:
        raise ProcessError("Stellar: max length of a key is 64 bytes")
    write_string(w, msg.key)
    write_bool(w, bool(msg.value))
    if msg.value:
        write_string(w, msg.value)


def write_manage_buy_offer_op(w: Writer, msg: StellarManageBuyOfferOp) -> None:
    _write_manage_offer_op_common(w, msg)


def write_manage_sell_offer_op(w: Writer, msg: StellarManageSellOfferOp) -> None:
    _write_manage_offer_op_common(w, msg)


def _write_manage_offer_op_common(
    w: Writer, msg: StellarManageSellOfferOp | StellarManageBuyOfferOp
) -> None:
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    write_uint64(w, msg.amount)  # amount to sell / buy
    write_uint32(w, msg.price_n)  # numerator
    write_uint32(w, msg.price_d)  # denominator
    write_uint64(w, msg.offer_id)


def write_path_payment_strict_receive_op(
    w: Writer, msg: StellarPathPaymentStrictReceiveOp
) -> None:
    _write_asset(w, msg.send_asset)
    write_uint64(w, msg.send_max)
    write_pubkey(w, msg.destination_account)

    _write_asset(w, msg.destination_asset)
    write_uint64(w, msg.destination_amount)
    write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _write_asset(w, p)


def write_path_payment_strict_send_op(
    w: Writer, msg: StellarPathPaymentStrictSendOp
) -> None:
    _write_asset(w, msg.send_asset)
    write_uint64(w, msg.send_amount)
    write_pubkey(w, msg.destination_account)

    _write_asset(w, msg.destination_asset)
    write_uint64(w, msg.destination_min)
    write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _write_asset(w, p)


def write_payment_op(w: Writer, msg: StellarPaymentOp) -> None:
    write_pubkey(w, msg.destination_account)
    _write_asset(w, msg.asset)
    write_uint64(w, msg.amount)


def write_set_options_op(w: Writer, msg: StellarSetOptionsOp) -> None:
    # inflation destination
    if msg.inflation_destination_account is None:
        write_bool(w, False)
    else:
        write_bool(w, True)
        write_pubkey(w, msg.inflation_destination_account)

    # NOTE: saves 21 bytes compared to hardcoding the operations
    for option in (
        # clear flags
        msg.clear_flags,
        # set flags
        msg.set_flags,
        # account thresholds
        msg.master_weight,
        msg.low_threshold,
        msg.medium_threshold,
        msg.high_threshold,
    ):
        if option is None:
            write_bool(w, False)
        else:
            write_bool(w, True)
            write_uint32(w, option)

    # home domain
    if msg.home_domain is None:
        write_bool(w, False)
    else:
        write_bool(w, True)
        if len(msg.home_domain) > 32:
            raise ProcessError("Stellar: max length of a home domain is 32 bytes")
        write_string(w, msg.home_domain)

    # signer
    if msg.signer_type is None:
        write_bool(w, False)
    else:
        if msg.signer_key is None or msg.signer_weight is None:
            raise DataError(
                "Stellar: signer_type, signer_key, signer_weight must be set together"
            )
        write_bool(w, True)
        write_uint32(w, msg.signer_type)
        write_bytes_fixed(w, msg.signer_key, 32)
        write_uint32(w, msg.signer_weight)


def write_claim_claimable_balance_op(
    w: Writer, msg: StellarClaimClaimableBalanceOp
) -> None:
    _write_claimable_balance_id(w, msg.balance_id)


def write_account(w: Writer, source_account: str | None) -> None:
    if source_account is None:
        write_bool(w, False)
    else:
        write_bool(w, True)
        write_pubkey(w, source_account)


def _write_asset_code(
    w: Writer, asset_type: StellarAssetType, asset_code: str | None
) -> None:
    if asset_type == StellarAssetType.NATIVE:
        return  # nothing is needed

    if asset_code is None:
        raise DataError("Stellar: invalid asset")

    code = asset_code.encode()
    if asset_type == StellarAssetType.ALPHANUM4:
        if len(code) > 4:
            raise DataError("Stellar: asset code too long for ALPHANUM4")
        # pad with zeros to 4 chars
        write_bytes_fixed(w, code + bytes([0] * (4 - len(code))), 4)
    elif asset_type == StellarAssetType.ALPHANUM12:
        if len(code) > 12:
            raise DataError("Stellar: asset code too long for ALPHANUM12")
        # pad with zeros to 12 chars
        write_bytes_fixed(w, code + bytes([0] * (12 - len(code))), 12)
    else:
        raise ProcessError("Stellar: invalid asset type")


def _write_asset(w: Writer, asset: StellarAsset) -> None:
    if asset.type == StellarAssetType.NATIVE:
        write_uint32(w, 0)
        return
    if asset.code is None or asset.issuer is None:
        raise DataError("Stellar: invalid asset")
    write_uint32(w, asset.type)
    _write_asset_code(w, asset.type, asset.code)
    write_pubkey(w, asset.issuer)


def _write_claimable_balance_id(w: Writer, claimable_balance_id: AnyBytes) -> None:
    if len(claimable_balance_id) != 36:  # 4 bytes type + 32 bytes data
        raise DataError("Stellar: invalid claimable balance id length")
    if claimable_balance_id[:4] != b"\x00\x00\x00\x00":  # CLAIMABLE_BALANCE_ID_TYPE_V0
        raise DataError("Stellar: invalid claimable balance id, unknown type")
    write_bytes_fixed(w, claimable_balance_id, 36)


def write_invoke_host_function_op(w: Writer, msg: StellarInvokeHostFunctionOp) -> None:
    _write_host_function(w, msg.function)
    # auth array
    write_uint32(w, len(msg.auth))
    for entry in msg.auth:
        _write_soroban_authorization_entry(w, entry)


def _write_host_function(w: Writer, msg: StellarHostFunction) -> None:
    from trezor.enums import StellarHostFunctionType

    write_uint32(w, msg.type)
    if msg.type == StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        if msg.invoke_contract is None:
            raise DataError("Stellar: missing invoke_contract")
        _write_invoke_contract_args(w, msg.invoke_contract)
    else:
        raise ProcessError("Stellar: unsupported host function type")


def _write_invoke_contract_args(w: Writer, msg: StellarInvokeContractArgs) -> None:
    _write_sc_address(w, msg.contract_address)
    _write_sc_symbol(w, msg.function_name)
    # args array
    write_uint32(w, len(msg.args))
    for arg in msg.args:
        _write_sc_val(w, arg)


def _write_sc_address(w: Writer, msg: StellarSCAddress) -> None:
    from trezor.enums import StellarSCAddressType

    write_uint32(w, msg.type)
    if msg.type == StellarSCAddressType.SC_ADDRESS_TYPE_ACCOUNT:
        # AccountID is a PublicKey: KEY_TYPE_ED25519 (0) + 32 bytes ed25519
        write_uint32(w, 0)  # KEY_TYPE_ED25519
        write_bytes_fixed(w, msg.address, 32)
    elif msg.type == StellarSCAddressType.SC_ADDRESS_TYPE_CONTRACT:
        # ContractID is a Hash (32 bytes)
        write_bytes_fixed(w, msg.address, 32)
    elif msg.type == StellarSCAddressType.SC_ADDRESS_TYPE_MUXED_ACCOUNT:
        # MuxedEd25519Account: { id: uint64, ed25519: uint256 }
        # address format: 32 bytes ed25519 + 8 bytes id
        if len(msg.address) != 40:
            raise DataError("Stellar: invalid muxed account address length")
        write_bytes_fixed(w, msg.address[32:40], 8)  # id (uint64)
        write_bytes_fixed(w, msg.address[0:32], 32)  # ed25519
    elif msg.type == StellarSCAddressType.SC_ADDRESS_TYPE_CLAIMABLE_BALANCE:
        # ClaimableBalanceID: { type: uint32, v0: Hash }
        # address format: 1 byte type + 32 bytes hash (from strkey decoding)
        if len(msg.address) != 33:
            raise DataError("Stellar: invalid claimable balance address length")
        if msg.address[0:1] != b"\x00":
            raise DataError("Stellar: unsupported claimable balance ID type")
        write_uint32(w, 0)  # CLAIMABLE_BALANCE_ID_TYPE_V0
        write_bytes_fixed(w, msg.address[1:33], 32)  # v0 hash
    elif msg.type == StellarSCAddressType.SC_ADDRESS_TYPE_LIQUIDITY_POOL:
        # PoolID is a Hash (32 bytes)
        write_bytes_fixed(w, msg.address, 32)
    else:
        raise ProcessError("Stellar: unsupported SC address type")


def _write_sc_symbol(w: Writer, symbol: str) -> None:
    # SCSymbol is a string with max 32 chars
    if len(symbol) > 32:
        raise DataError("Stellar: symbol too long")
    write_string(w, symbol)


def _write_sc_val(w: Writer, msg: StellarSCVal) -> None:
    from trezor.enums import StellarSCValType

    write_uint32(w, msg.type)

    if msg.type == StellarSCValType.SCV_BOOL:
        write_bool(w, msg.b if msg.b is not None else False)
    elif msg.type == StellarSCValType.SCV_VOID:
        pass  # no data
    elif msg.type == StellarSCValType.SCV_U32:
        if msg.u32 is None:
            raise DataError("Stellar: missing u32 value")
        write_uint32(w, msg.u32)
    elif msg.type == StellarSCValType.SCV_I32:
        if msg.i32 is None:
            raise DataError("Stellar: missing i32 value")
        write_int32(w, msg.i32)
    elif msg.type == StellarSCValType.SCV_U64:
        if msg.u64 is None:
            raise DataError("Stellar: missing u64 value")
        write_uint64(w, msg.u64)
    elif msg.type == StellarSCValType.SCV_I64:
        if msg.i64 is None:
            raise DataError("Stellar: missing i64 value")
        write_int64(w, msg.i64)
    elif msg.type == StellarSCValType.SCV_TIMEPOINT:
        if msg.timepoint is None:
            raise DataError("Stellar: missing timepoint value")
        write_uint64(w, msg.timepoint)
    elif msg.type == StellarSCValType.SCV_DURATION:
        if msg.duration is None:
            raise DataError("Stellar: missing duration value")
        write_uint64(w, msg.duration)
    elif msg.type == StellarSCValType.SCV_U128:
        if msg.u128 is None:
            raise DataError("Stellar: missing u128 value")
        _write_uint128_parts(w, msg.u128)
    elif msg.type == StellarSCValType.SCV_I128:
        if msg.i128 is None:
            raise DataError("Stellar: missing i128 value")
        _write_int128_parts(w, msg.i128)
    elif msg.type == StellarSCValType.SCV_U256:
        if msg.u256 is None:
            raise DataError("Stellar: missing u256 value")
        _write_uint256_parts(w, msg.u256)
    elif msg.type == StellarSCValType.SCV_I256:
        if msg.i256 is None:
            raise DataError("Stellar: missing i256 value")
        _write_int256_parts(w, msg.i256)
    elif msg.type == StellarSCValType.SCV_BYTES:
        if msg.bytes is None:
            raise DataError("Stellar: missing bytes value")
        write_string(w, msg.bytes)
    elif msg.type == StellarSCValType.SCV_STRING:
        if msg.string is None:
            raise DataError("Stellar: missing string value")
        write_string(w, msg.string)
    elif msg.type == StellarSCValType.SCV_SYMBOL:
        if msg.symbol is None:
            raise DataError("Stellar: missing symbol value")
        _write_sc_symbol(w, msg.symbol)
    elif msg.type == StellarSCValType.SCV_VEC:
        # vec is optional in XDR (SCVec*)
        write_bool(w, True)  # present
        write_uint32(w, len(msg.vec))
        for item in msg.vec:
            _write_sc_val(w, item)
    elif msg.type == StellarSCValType.SCV_MAP:
        # map is optional in XDR (SCMap*)
        write_bool(w, True)  # present
        write_uint32(w, len(msg.map))
        for entry in msg.map:
            if entry.key is None or entry.value is None:
                raise DataError("Stellar: map entry missing key or value")
            _write_sc_val(w, entry.key)
            _write_sc_val(w, entry.value)
    elif msg.type == StellarSCValType.SCV_ADDRESS:
        if msg.address is None:
            raise DataError("Stellar: missing address value")
        _write_sc_address(w, msg.address)
    else:
        raise ProcessError("Stellar: unsupported SCVal type")


def _write_uint128_parts(w: Writer, msg: StellarUInt128Parts) -> None:
    write_uint64(w, msg.hi)
    write_uint64(w, msg.lo)


def _write_int128_parts(w: Writer, msg: StellarInt128Parts) -> None:
    write_int64(w, msg.hi)
    write_uint64(w, msg.lo)


def _write_uint256_parts(w: Writer, msg: StellarUInt256Parts) -> None:
    write_uint64(w, msg.hi_hi)
    write_uint64(w, msg.hi_lo)
    write_uint64(w, msg.lo_hi)
    write_uint64(w, msg.lo_lo)


def _write_int256_parts(w: Writer, msg: StellarInt256Parts) -> None:
    write_int64(w, msg.hi_hi)
    write_uint64(w, msg.hi_lo)
    write_uint64(w, msg.lo_hi)
    write_uint64(w, msg.lo_lo)


def _write_soroban_authorization_entry(
    w: Writer, msg: StellarSorobanAuthorizationEntry
) -> None:
    _write_soroban_credentials(w, msg.credentials)
    _write_soroban_authorized_invocation(w, msg.root_invocation)


def _write_soroban_credentials(w: Writer, msg: StellarSorobanCredentials) -> None:
    from trezor.enums import StellarSorobanCredentialsType

    write_uint32(w, msg.type)
    if msg.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT:
        pass  # void
    elif msg.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS:
        if msg.address is None:
            raise DataError("Stellar: missing address credentials")
        _write_soroban_address_credentials(w, msg.address)
    else:
        raise ProcessError("Stellar: unsupported credentials type")


def _write_soroban_address_credentials(
    w: Writer, msg: StellarSorobanAddressCredentials
) -> None:
    _write_sc_address(w, msg.address)
    write_int64(w, msg.nonce)
    write_uint32(w, msg.signature_expiration_ledger)
    _write_sc_val(w, msg.signature)


def _write_soroban_authorized_invocation(
    w: Writer, msg: StellarSorobanAuthorizedInvocation
) -> None:
    _write_soroban_authorized_function(w, msg.function)
    # sub_invocations array
    write_uint32(w, len(msg.sub_invocations))
    for sub in msg.sub_invocations:
        _write_soroban_authorized_invocation(w, sub)


def _write_soroban_authorized_function(
    w: Writer, msg: StellarSorobanAuthorizedFunction
) -> None:
    from trezor.enums import StellarSorobanAuthorizedFunctionType

    write_uint32(w, msg.type)
    if (
        msg.type
        == StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        if msg.contract_fn is None:
            raise DataError("Stellar: missing contract_fn")
        _write_invoke_contract_args(w, msg.contract_fn)
    else:
        raise ProcessError("Stellar: unsupported authorized function type")
