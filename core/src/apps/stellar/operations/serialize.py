from trezor.enums import StellarAssetType
from trezor.messages import (
    StellarAccountMergeOp,
    StellarAllowTrustOp,
    StellarAsset,
    StellarBumpSequenceOp,
    StellarChangeTrustOp,
    StellarCreateAccountOp,
    StellarCreatePassiveSellOfferOp,
    StellarManageBuyOfferOp,
    StellarManageDataOp,
    StellarManageSellOfferOp,
    StellarPathPaymentStrictReceiveOp,
    StellarPathPaymentStrictSendOp,
    StellarPaymentOp,
    StellarSetOptionsOp,
)
from trezor.wire import DataError, ProcessError

from .. import writers

if False:
    from trezor.utils import Writer


def write_account_merge_op(w: Writer, msg: StellarAccountMergeOp) -> None:
    writers.write_pubkey(w, msg.destination_account)


def write_allow_trust_op(w: Writer, msg: StellarAllowTrustOp) -> None:
    # trustor account (the account being allowed to access the asset)
    writers.write_pubkey(w, msg.trusted_account)
    writers.write_uint32(w, msg.asset_type)
    _write_asset_code(w, msg.asset_type, msg.asset_code)

    writers.write_bool(w, msg.is_authorized)


def write_bump_sequence_op(w: Writer, msg: StellarBumpSequenceOp) -> None:
    writers.write_uint64(w, msg.bump_to)


def write_change_trust_op(w: Writer, msg: StellarChangeTrustOp) -> None:
    _write_asset(w, msg.asset)
    writers.write_uint64(w, msg.limit)


def write_create_account_op(w: Writer, msg: StellarCreateAccountOp) -> None:
    writers.write_pubkey(w, msg.new_account)
    writers.write_uint64(w, msg.starting_balance)


def write_create_passive_sell_offer_op(
    w: Writer, msg: StellarCreatePassiveSellOfferOp
) -> None:
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    writers.write_uint64(w, msg.amount)
    writers.write_uint32(w, msg.price_n)
    writers.write_uint32(w, msg.price_d)


def write_manage_data_op(w: Writer, msg: StellarManageDataOp) -> None:
    if len(msg.key) > 64:
        raise ProcessError("Stellar: max length of a key is 64 bytes")
    writers.write_string(w, msg.key)
    writers.write_bool(w, bool(msg.value))
    if msg.value:
        writers.write_string(w, msg.value)


def write_manage_buy_offer_op(w: Writer, msg: StellarManageBuyOfferOp) -> None:
    _write_manage_offer_op_common(w, msg)


def write_manage_sell_offer_op(w: Writer, msg: StellarManageSellOfferOp) -> None:
    _write_manage_offer_op_common(w, msg)


def _write_manage_offer_op_common(
    w: Writer, msg: StellarManageSellOfferOp | StellarManageBuyOfferOp
) -> None:
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    writers.write_uint64(w, msg.amount)  # amount to sell / buy
    writers.write_uint32(w, msg.price_n)  # numerator
    writers.write_uint32(w, msg.price_d)  # denominator
    writers.write_uint64(w, msg.offer_id)


def write_path_payment_strict_receive_op(
    w: Writer, msg: StellarPathPaymentStrictReceiveOp
) -> None:
    _write_asset(w, msg.send_asset)
    writers.write_uint64(w, msg.send_max)
    writers.write_pubkey(w, msg.destination_account)

    _write_asset(w, msg.destination_asset)
    writers.write_uint64(w, msg.destination_amount)
    writers.write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _write_asset(w, p)


def write_path_payment_strict_send_op(
    w: Writer, msg: StellarPathPaymentStrictSendOp
) -> None:
    _write_asset(w, msg.send_asset)
    writers.write_uint64(w, msg.send_amount)
    writers.write_pubkey(w, msg.destination_account)

    _write_asset(w, msg.destination_asset)
    writers.write_uint64(w, msg.destination_min)
    writers.write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _write_asset(w, p)


def write_payment_op(w: Writer, msg: StellarPaymentOp) -> None:
    writers.write_pubkey(w, msg.destination_account)
    _write_asset(w, msg.asset)
    writers.write_uint64(w, msg.amount)


def write_set_options_op(w: Writer, msg: StellarSetOptionsOp) -> None:
    # inflation destination
    if msg.inflation_destination_account is None:
        writers.write_bool(w, False)
    else:
        writers.write_bool(w, True)
        writers.write_pubkey(w, msg.inflation_destination_account)

    # clear flags
    _write_set_options_int(w, msg.clear_flags)
    # set flags
    _write_set_options_int(w, msg.set_flags)
    # account thresholds
    _write_set_options_int(w, msg.master_weight)
    _write_set_options_int(w, msg.low_threshold)
    _write_set_options_int(w, msg.medium_threshold)
    _write_set_options_int(w, msg.high_threshold)

    # home domain
    if msg.home_domain is None:
        writers.write_bool(w, False)
    else:
        writers.write_bool(w, True)
        if len(msg.home_domain) > 32:
            raise ProcessError("Stellar: max length of a home domain is 32 bytes")
        writers.write_string(w, msg.home_domain)

    # signer
    if msg.signer_type is None:
        writers.write_bool(w, False)
    else:
        if msg.signer_key is None or msg.signer_weight is None:
            raise DataError(
                "Stellar: signer_type, signer_key, signer_weight must be set together"
            )
        writers.write_bool(w, True)
        writers.write_uint32(w, msg.signer_type)
        writers.write_bytes_fixed(w, msg.signer_key, 32)
        writers.write_uint32(w, msg.signer_weight)


def _write_set_options_int(w: Writer, value: int | None) -> None:
    if value is None:
        writers.write_bool(w, False)
    else:
        writers.write_bool(w, True)
        writers.write_uint32(w, value)


def write_account(w: Writer, source_account: str | None) -> None:
    if source_account is None:
        writers.write_bool(w, False)
    else:
        writers.write_bool(w, True)
        writers.write_pubkey(w, source_account)


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
        writers.write_bytes_fixed(w, code + bytes([0] * (4 - len(code))), 4)
    elif asset_type == StellarAssetType.ALPHANUM12:
        if len(code) > 12:
            raise DataError("Stellar: asset code too long for ALPHANUM12")
        # pad with zeros to 12 chars
        writers.write_bytes_fixed(w, code + bytes([0] * (12 - len(code))), 12)
    else:
        raise ProcessError("Stellar: invalid asset type")


def _write_asset(w: Writer, asset: StellarAsset) -> None:
    if asset.type == StellarAssetType.NATIVE:
        writers.write_uint32(w, 0)
        return
    if asset.code is None or asset.issuer is None:
        raise DataError("Stellar: invalid asset")
    writers.write_uint32(w, asset.type)
    _write_asset_code(w, asset.type, asset.code)
    writers.write_pubkey(w, asset.issuer)
