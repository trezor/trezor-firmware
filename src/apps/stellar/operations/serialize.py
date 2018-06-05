from trezor.messages.StellarAccountMergeOp import StellarAccountMergeOp
from trezor.messages.StellarAssetType import StellarAssetType
from trezor.messages.StellarAllowTrustOp import StellarAllowTrustOp
from trezor.messages.StellarBumpSequenceOp import StellarBumpSequenceOp
from trezor.messages.StellarChangeTrustOp import StellarChangeTrustOp
from trezor.messages.StellarCreateAccountOp import StellarCreateAccountOp
from trezor.messages.StellarCreatePassiveOfferOp import StellarCreatePassiveOfferOp
from trezor.messages.StellarManageDataOp import StellarManageDataOp
from trezor.messages.StellarManageOfferOp import StellarManageOfferOp
from trezor.messages.StellarPathPaymentOp import StellarPathPaymentOp
from trezor.messages.StellarPaymentOp import StellarPaymentOp
from trezor.messages.StellarSetOptionsOp import StellarSetOptionsOp
from apps.stellar.consts import *
from apps.stellar.writers import *


def serialize_account_merge_op(w, msg: StellarAccountMergeOp):
    write_pubkey(w, msg.destination_account)


def serialize_allow_trust_op(w, msg: StellarAllowTrustOp):
    # trustor account (the account being allowed to access the asset)
    write_pubkey(w, msg.trusted_account)
    write_uint32(w, msg.asset_type)
    _serialize_asset_code(w, msg.asset_type, msg.asset_code)

    write_bool(w, msg.is_authorized)


def serialize_bump_sequence_op(w, msg: StellarBumpSequenceOp):
    write_uint64(w, msg.bump_to)


def serialize_change_trust_op(w, msg: StellarChangeTrustOp):
    _serialize_asset(w, msg.asset)
    write_uint64(w, msg.limit)


def serialize_create_account_op(w, msg: StellarCreateAccountOp):
    write_pubkey(w, msg.new_account)
    write_uint64(w, msg.starting_balance)


def serialize_create_passive_offer_op(w, msg: StellarCreatePassiveOfferOp):
    _serialize_asset(w, msg.selling_asset)
    _serialize_asset(w, msg.buying_asset)
    write_uint64(w, msg.amount)
    write_uint32(w, msg.price_n)
    write_uint32(w, msg.price_d)


def serialize_manage_data_op(w, msg: StellarManageDataOp):
    if len(msg.key) > 64:
        raise ValueError('Stellar: max length of a key is 64 bytes')
    write_string(w, msg.key)
    write_bool(w, bool(msg.value))
    if msg.value:
        write_uint32(w, len(msg.value))
        write_bytes(w, msg.value)


def serialize_manage_offer_op(w, msg: StellarManageOfferOp):
    _serialize_asset(w, msg.selling_asset)
    _serialize_asset(w, msg.buying_asset)
    write_uint64(w, msg.amount)  # amount to sell
    write_uint32(w, msg.price_n)  # numerator
    write_uint32(w, msg.price_d)  # denominator
    write_uint64(w, msg.offer_id)


def serialize_path_payment_op(w, msg: StellarPathPaymentOp):
    _serialize_asset(w, msg.send_asset)
    write_uint64(w, msg.send_max)
    write_pubkey(w, msg.destination_account)

    _serialize_asset(w, msg.destination_asset)
    write_uint64(w, msg.destination_amount)
    write_uint32(w, len(msg.paths))
    for p in msg.paths:
        _serialize_asset(w, p)


def serialize_payment_op(w, msg: StellarPaymentOp):
    write_pubkey(w, msg.destination_account)
    _serialize_asset(w, msg.asset)
    write_uint64(w, msg.amount)


def serialize_set_options_op(w, msg: StellarSetOptionsOp):
    # inflation destination
    write_bool(w, bool(msg.inflation_destination_account))
    if msg.inflation_destination_account:
        write_pubkey(w, msg.inflation_destination_account)

    # clear flags
    write_bool(w, bool(msg.clear_flags))
    if msg.clear_flags:
        write_uint32(w, msg.clear_flags)

    # set flags
    write_bool(w, bool(msg.set_flags))
    if msg.set_flags:
        write_uint32(w, msg.set_flags)

    # account thresholds
    write_bool(w, bool(msg.master_weight))
    if msg.master_weight:
        write_uint32(w, msg.master_weight)

    write_bool(w, bool(msg.low_threshold))
    if msg.low_threshold:
        write_uint32(w, msg.low_threshold)

    write_bool(w, bool(msg.medium_threshold))
    if msg.medium_threshold:
        write_uint32(w, msg.medium_threshold)

    write_bool(w, bool(msg.high_threshold))
    if msg.high_threshold:
        write_uint32(w, msg.high_threshold)

    # home domain
    write_bool(w, bool(msg.home_domain))
    if msg.home_domain:
        if len(msg.home_domain) > 32:
            raise ValueError('Stellar: max length of a home domain is 32 bytes')
        write_string(w, msg.home_domain)

    # signer
    write_bool(w, bool(msg.signer_type))
    if msg.signer_type:
        # signer type
        write_uint32(w, msg.signer_type)
        write_bytes(w, msg.signer_key)
        write_uint32(w, msg.signer_weight)


def serialize_account(w, source_account: bytes):
    if source_account is None:
        write_bool(w, False)
        return
    write_pubkey(w, source_account)


def _serialize_asset_code(w, asset_type: int, asset_code: str):
    code = bytearray(asset_code)
    if asset_type == ASSET_TYPE_NATIVE:
        return  # nothing is needed
    elif asset_type == ASSET_TYPE_ALPHANUM4:
        # pad with zeros to 4 chars
        write_bytes(w, code + bytearray([0] * (4 - len(code))))
    elif asset_type == ASSET_TYPE_ALPHANUM12:
        # pad with zeros to 12 chars
        write_bytes(w, code + bytearray([0] * (12 - len(code))))
    else:
        raise ValueError('Stellar: invalid asset type')


def _serialize_asset(w, asset: StellarAssetType):
    if asset is None:
        write_uint32(w, 0)
        return
    write_uint32(w, asset.type)
    _serialize_asset_code(w, asset.type, asset.code)
    write_pubkey(w, asset.issuer)
