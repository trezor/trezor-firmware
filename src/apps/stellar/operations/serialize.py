from trezor.messages.StellarAccountMergeOp import StellarAccountMergeOp
from trezor.messages.StellarAllowTrustOp import StellarAllowTrustOp
from trezor.messages.StellarAssetType import StellarAssetType
from trezor.messages.StellarBumpSequenceOp import StellarBumpSequenceOp
from trezor.messages.StellarChangeTrustOp import StellarChangeTrustOp
from trezor.messages.StellarCreateAccountOp import StellarCreateAccountOp
from trezor.messages.StellarCreatePassiveOfferOp import StellarCreatePassiveOfferOp
from trezor.messages.StellarManageDataOp import StellarManageDataOp
from trezor.messages.StellarManageOfferOp import StellarManageOfferOp
from trezor.messages.StellarPathPaymentOp import StellarPathPaymentOp
from trezor.messages.StellarPaymentOp import StellarPaymentOp
from trezor.messages.StellarSetOptionsOp import StellarSetOptionsOp
from trezor.wire import ProcessError

from apps.stellar import consts, writers


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
        writers.write_uint32(w, len(msg.value))
        writers.write_bytes(w, msg.value)


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
    writers.write_bool(w, bool(msg.inflation_destination_account))
    if msg.inflation_destination_account:
        writers.write_pubkey(w, msg.inflation_destination_account)

    # clear flags
    writers.write_bool(w, bool(msg.clear_flags))
    if msg.clear_flags:
        writers.write_uint32(w, msg.clear_flags)

    # set flags
    writers.write_bool(w, bool(msg.set_flags))
    if msg.set_flags:
        writers.write_uint32(w, msg.set_flags)

    # account thresholds
    writers.write_bool(w, bool(msg.master_weight))
    if msg.master_weight:
        writers.write_uint32(w, msg.master_weight)

    writers.write_bool(w, bool(msg.low_threshold))
    if msg.low_threshold:
        writers.write_uint32(w, msg.low_threshold)

    writers.write_bool(w, bool(msg.medium_threshold))
    if msg.medium_threshold:
        writers.write_uint32(w, msg.medium_threshold)

    writers.write_bool(w, bool(msg.high_threshold))
    if msg.high_threshold:
        writers.write_uint32(w, msg.high_threshold)

    # home domain
    writers.write_bool(w, bool(msg.home_domain))
    if msg.home_domain:
        if len(msg.home_domain) > 32:
            raise ProcessError("Stellar: max length of a home domain is 32 bytes")
        writers.write_string(w, msg.home_domain)

    # signer
    writers.write_bool(w, bool(msg.signer_type))
    if msg.signer_type:
        # signer type
        writers.write_uint32(w, msg.signer_type)
        writers.write_bytes(w, msg.signer_key)
        writers.write_uint32(w, msg.signer_weight)


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
        writers.write_bytes(w, code + bytearray([0] * (4 - len(code))))
    elif asset_type == consts.ASSET_TYPE_ALPHANUM12:
        # pad with zeros to 12 chars
        writers.write_bytes(w, code + bytearray([0] * (12 - len(code))))
    else:
        raise ProcessError("Stellar: invalid asset type")


def _write_asset(w, asset: StellarAssetType):
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        writers.write_uint32(w, 0)
        return
    writers.write_uint32(w, asset.type)
    _write_asset_code(w, asset.type, asset.code)
    writers.write_pubkey(w, asset.issuer)
