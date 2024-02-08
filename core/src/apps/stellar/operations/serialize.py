from typing import TYPE_CHECKING

from trezor.enums import (
    StellarAssetType,
    StellarHostFunctionType,
    StellarSorobanCredentialsType,
)
from trezor.wire import DataError, ProcessError

from ..writers import (
    write_bool,
    write_bytes_fixed,
    write_int64,
    write_invoke_contract_args,
    write_pubkey,
    write_sc_address,
    write_sc_val,
    write_soroban_authorized_invocation,
    write_string,
    write_uint32,
    write_uint64,
)

if TYPE_CHECKING:
    from trezor.messages import (
        StellarAccountMergeOp,
        StellarAllowTrustOp,
        StellarAsset,
        StellarBumpSequenceOp,
        StellarChangeTrustOp,
        StellarClaimClaimableBalanceOp,
        StellarCreateAccountOp,
        StellarCreatePassiveSellOfferOp,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSetOptionsOp,
        StellarSorobanAddressCredentials,
        StellarSorobanAuthorizationEntry,
        StellarSorobanCredentials,
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


def write_invoke_host_function_op(w: Writer, msg: StellarInvokeHostFunctionOp) -> None:
    # write host_function
    if msg.function.type != StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        raise DataError(f"Stellar: unsupported host function type: {msg.function.type}")
    write_uint32(w, msg.function.type)
    assert msg.function.invoke_contract
    write_invoke_contract_args(w, msg.function.invoke_contract)

    # write auth
    write_uint32(w, len(msg.auth))
    for auth in msg.auth:
        write_soroban_authorization_entry(w, auth)


def write_soroban_address_credentials(
    w: Writer, credentials: StellarSorobanAddressCredentials
) -> None:
    write_sc_address(w, credentials.address)
    write_int64(w, credentials.nonce)
    write_uint32(w, credentials.signature_expiration_ledger)
    write_sc_val(w, credentials.signature)


def write_soroban_credentials(
    w: Writer, credentials: StellarSorobanCredentials
) -> None:
    write_uint32(w, credentials.type)
    if (
        credentials.type
        == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT
    ):
        pass  # nothing to write
    elif credentials.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS:
        assert credentials.address
        write_soroban_address_credentials(w, credentials.address)
    else:
        raise DataError(f"Stellar: unsupported credentials type: {credentials}")


def write_soroban_authorization_entry(
    w: Writer, entry: StellarSorobanAuthorizationEntry
) -> None:
    write_soroban_credentials(w, entry.credentials)
    write_soroban_authorized_invocation(w, entry.root_invocation)


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


def _write_claimable_balance_id(w: Writer, claimable_balance_id: bytes) -> None:
    if len(claimable_balance_id) != 36:  # 4 bytes type + 32 bytes data
        raise DataError("Stellar: invalid claimable balance id length")
    if claimable_balance_id[:4] != b"\x00\x00\x00\x00":  # CLAIMABLE_BALANCE_ID_TYPE_V0
        raise DataError("Stellar: invalid claimable balance id, unknown type")
    write_bytes_fixed(w, claimable_balance_id, 36)
