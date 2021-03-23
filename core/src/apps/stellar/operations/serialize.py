from trezor.messages import (
    StellarAccountMergeOp,
    StellarAllowTrustOp,
    StellarAssetType,
    StellarBumpSequenceOp,
    StellarChangeTrustOp,
    StellarCreateAccountOp,
    StellarCreatePassiveOfferOp,
    StellarManageDataOp,
    StellarManageOfferOp,
    StellarPathPaymentOp,
    StellarPaymentOp,
    StellarSetOptionsOp,
)
from trezor.wire import ProcessError

from .. import consts, writers


def write_account_merge_op(w, msg: StellarAccountMergeOp):
    writers.write_pubkey(w, msg.destination_account)


def write_allow_trust_op(w, msg: StellarAllowTrustOp):
    # trustor account (the account being allowed to access the asset)
    writers.write_pubkey(w, msg.trusted_account)
    writers.write_uint32(w, msg.asset_type)
    _write_asset_code(w, msg.asset_type, msg.asset_code)

    writers.write_bool(w, msg.is_authorized)


def write_bump_sequence_op(w, msg: StellarBumpSequenceOp):
    writers.write_uint64(w, msg.bump_to)


def write_change_trust_op(w, msg: StellarChangeTrustOp):
    _write_asset(w, msg.asset)
    writers.write_uint64(w, msg.limit)


def write_create_account_op(w, msg: StellarCreateAccountOp):
    writers.write_pubkey(w, msg.new_account)
    writers.write_uint64(w, msg.starting_balance)


def write_create_passive_offer_op(w, msg: StellarCreatePassiveOfferOp):
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    writers.write_uint64(w, msg.amount)
    writers.write_uint32(w, msg.price_n)
    writers.write_uint32(w, msg.price_d)


def write_manage_data_op(w, msg: StellarManageDataOp):
    if len(msg.key) > 64:
        raise ProcessError("Stellar: max length of a key is 64 bytes")
    writers.write_string(w, msg.key)
    writers.write_bool(w, bool(msg.value))
    if msg.value:
        writers.write_string(w, msg.value)


def write_manage_offer_op(w, msg: StellarManageOfferOp):
    _write_asset(w, msg.selling_asset)
    _write_asset(w, msg.buying_asset)
    writers.write_uint64(w, msg.amount)  # amount to sell
    writers.write_uint32(w, msg.price_n)  # numerator
    writers.write_uint32(w, msg.price_d)  # denominator
    writers.write_uint64(w, msg.offer_id)


def write_path_payment_op(w, msg: StellarPathPaymentOp):
    _write_asset(w, msg.send_asset)
    writers.write_uint64(w, msg.send_max)
    writers.write_pubkey(w, msg.destination_account)

    _write_asset(w, msg.destination_asset)
    writers.write_uint64(w, msg.destination_amount)
    writers.write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _write_asset(w, p)


def write_payment_op(w, msg: StellarPaymentOp):
    writers.write_pubkey(w, msg.destination_account)
    _write_asset(w, msg.asset)
    writers.write_uint64(w, msg.amount)


def write_set_options_op(w, msg: StellarSetOptionsOp):
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
    elif msg.signer_type in consts.SIGN_TYPES:
        writers.write_bool(w, True)
        writers.write_uint32(w, msg.signer_type)
        writers.write_bytes_fixed(w, msg.signer_key, 32)
        writers.write_uint32(w, msg.signer_weight)
    else:
        raise ProcessError("Stellar: unknown signer type")


def _write_set_options_int(w, value: int):
    if value is None:
        writers.write_bool(w, False)
    else:
        writers.write_bool(w, True)
        writers.write_uint32(w, value)


def write_account(w, source_account: str):
    if source_account is None:
        writers.write_bool(w, False)
        return
    writers.write_pubkey(w, source_account)


def _write_asset_code(w, asset_type: int, asset_code: str):
    code = bytearray(asset_code)
    if asset_type == consts.ASSET_TYPE_NATIVE:
        return  # nothing is needed
    elif asset_type == consts.ASSET_TYPE_ALPHANUM4:
        # pad with zeros to 4 chars
        writers.write_bytes_fixed(w, code + bytearray([0] * (4 - len(code))), 4)
    elif asset_type == consts.ASSET_TYPE_ALPHANUM12:
        # pad with zeros to 12 chars
        writers.write_bytes_fixed(w, code + bytearray([0] * (12 - len(code))), 12)
    else:
        raise ProcessError("Stellar: invalid asset type")


def _write_asset(w, asset: StellarAssetType):
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        writers.write_uint32(w, 0)
        return
    writers.write_uint32(w, asset.type)
    _write_asset_code(w, asset.type, asset.code)
    writers.write_pubkey(w, asset.issuer)
