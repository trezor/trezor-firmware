import gc
from micropython import const

from trezor import utils
from trezor.crypto import base58, bip32, cashaddr, der
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import blake256, sha256
from trezor.messages import FailureType, InputScriptType, OutputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType

from apps.common import address_type, coininfo, coins, seed
from apps.wallet.sign_tx import (
    addresses,
    decred,
    helpers,
    multisig,
    progress,
    scripts,
    segwit_bip143,
    tx_weight,
    writers,
    zcash,
)

# the number of bip32 levels used in a wallet (chain and address)
_BIP32_WALLET_DEPTH = const(2)

# the chain id used for change
_BIP32_CHANGE_CHAIN = const(1)

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
_BIP32_MAX_LAST_ELEMENT = const(1000000)


class SigningError(ValueError):
    pass


# Transaction signing
# ===
# see https://github.com/trezor/trezor-mcu/blob/master/firmware/signing.c#L84
# for pseudo code overview
# ===


# Phase 1
# - check inputs, previous transactions, and outputs
# - ask for confirmations
# - check fee
async def check_tx_fee(tx: SignTx, keychain: seed.Keychain):
    coin = coins.by_name(tx.coin_name)

    # h_first is used to make sure the inputs and outputs streamed in Phase 1
    # are the same as in Phase 2.  it is thus not required to fully hash the
    # tx, as the SignTx info is streamed only once
    h_first = utils.HashWriter(sha256())  # not a real tx hash

    if coin.decred:
        hash143 = decred.DecredPrefixHasher(tx)  # pseudo BIP-0143 prefix hashing
        tx_ser = TxRequestSerializedType()
    elif tx.overwintered:
        if tx.version == 3:
            branch_id = tx.branch_id or 0x5BA81B19  # Overwinter
            hash143 = zcash.Zip143(branch_id)  # ZIP-0143 transaction hashing
        elif tx.version == 4:
            branch_id = tx.branch_id or 0x76B809BB  # Sapling
            hash143 = zcash.Zip243(branch_id)  # ZIP-0243 transaction hashing
        else:
            raise SigningError(
                FailureType.DataError,
                "Unsupported version for overwintered transaction",
            )
    else:
        hash143 = segwit_bip143.Bip143()  # BIP-0143 transaction hashing

    multifp = multisig.MultisigFingerprint()  # control checksum of multisig inputs
    weight = tx_weight.TxWeightCalculator(tx.inputs_count, tx.outputs_count)

    total_in = 0  # sum of input amounts
    segwit_in = 0  # sum of segwit input amounts
    total_out = 0  # sum of output amounts
    change_out = 0  # change output amount
    wallet_path = []  # common prefix of input paths
    segwit = {}  # dict of booleans stating if input is segwit

    # output structures
    txo_bin = TxOutputBinType()
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()

    for i in range(tx.inputs_count):
        progress.advance()
        # STAGE_REQUEST_1_INPUT
        txi = await helpers.request_tx_input(tx_req, i)
        wallet_path = input_extract_wallet_path(txi, wallet_path)
        writers.write_tx_input_check(h_first, txi)
        weight.add_input(txi)
        hash143.add_prevouts(txi)  # all inputs are included (non-segwit as well)
        hash143.add_sequence(txi)

        if not addresses.validate_full_path(txi.address_n, coin, txi.script_type):
            await helpers.confirm_foreign_address(txi.address_n)

        if txi.multisig:
            multifp.add(txi.multisig)

        if txi.script_type in (
            InputScriptType.SPENDWITNESS,
            InputScriptType.SPENDP2SHWITNESS,
        ):
            if not coin.segwit:
                raise SigningError(
                    FailureType.DataError, "Segwit not enabled on this coin"
                )
            if not txi.amount:
                raise SigningError(FailureType.DataError, "Segwit input without amount")
            segwit[i] = True
            segwit_in += txi.amount
            total_in += txi.amount

        elif txi.script_type in (
            InputScriptType.SPENDADDRESS,
            InputScriptType.SPENDMULTISIG,
        ):
            if coin.force_bip143 or tx.overwintered:
                if not txi.amount:
                    raise SigningError(
                        FailureType.DataError, "Expected input with amount"
                    )
                segwit[i] = False
                segwit_in += txi.amount
                total_in += txi.amount
            else:
                segwit[i] = False
                total_in += await get_prevtx_output_value(
                    coin, tx_req, txi.prev_hash, txi.prev_index
                )

        else:
            raise SigningError(FailureType.DataError, "Wrong input script type")

        if coin.decred:
            w_txi = writers.empty_bytearray(8 if i == 0 else 0 + 9 + len(txi.prev_hash))
            if i == 0:  # serializing first input => prepend headers
                writers.write_bytes(w_txi, get_tx_header(coin, tx))
            writers.write_tx_input_decred(w_txi, txi)
            tx_ser.serialized_tx = w_txi
            tx_req.serialized = tx_ser

    if coin.decred:
        hash143.add_output_count(tx)

    for o in range(tx.outputs_count):
        # STAGE_REQUEST_3_OUTPUT
        txo = await helpers.request_tx_output(tx_req, o)
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, keychain)
        weight.add_output(txo_bin.script_pubkey)

        if change_out == 0 and output_is_change(txo, wallet_path, segwit_in, multifp):
            # output is change and does not need confirmation
            change_out = txo.amount
        elif not await helpers.confirm_output(txo, coin):
            raise SigningError(FailureType.ActionCancelled, "Output cancelled")

        if coin.decred:
            if txo.decred_script_version is not None and txo.decred_script_version != 0:
                raise SigningError(
                    FailureType.ActionCancelled,
                    "Cannot send to output with script version != 0",
                )
            txo_bin.decred_script_version = txo.decred_script_version

            w_txo_bin = writers.empty_bytearray(
                4 + 8 + 2 + 4 + len(txo_bin.script_pubkey)
            )
            if o == 0:  # serializing first output => prepend outputs count
                writers.write_varint(w_txo_bin, tx.outputs_count)
            writers.write_tx_output(w_txo_bin, txo_bin)
            tx_ser.serialized_tx = w_txo_bin
            tx_req.serialized = tx_ser
            hash143.set_last_output_bytes(w_txo_bin)

        writers.write_tx_output(h_first, txo_bin)
        hash143.add_output(txo_bin)
        total_out += txo_bin.amount

    fee = total_in - total_out
    if fee < 0:
        raise SigningError(FailureType.NotEnoughFunds, "Not enough funds")

    # fee > (coin.maxfee per byte * tx size)
    if fee > (coin.maxfee_kb / 1000) * (weight.get_total() / 4):
        if not await helpers.confirm_feeoverthreshold(fee, coin):
            raise SigningError(FailureType.ActionCancelled, "Signing cancelled")

    if tx.lock_time > 0:
        if not await helpers.confirm_nondefault_locktime(tx.lock_time):
            raise SigningError(FailureType.ActionCancelled, "Locktime cancelled")

    if not await helpers.confirm_total(total_in - change_out, fee, coin):
        raise SigningError(FailureType.ActionCancelled, "Total cancelled")

    if coin.decred:
        hash143.add_locktime_expiry(tx)

    return h_first, hash143, segwit, total_in, wallet_path


async def sign_tx(tx: SignTx, keychain: seed.Keychain):
    tx = helpers.sanitize_sign_tx(tx)

    progress.init(tx.inputs_count, tx.outputs_count)

    # Phase 1

    h_first, hash143, segwit, authorized_in, wallet_path = await check_tx_fee(
        tx, keychain
    )

    # Phase 2
    # - sign inputs
    # - check that nothing changed

    coin = coins.by_name(tx.coin_name)
    tx_ser = TxRequestSerializedType()

    txo_bin = TxOutputBinType()
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()
    tx_req.serialized = None

    if coin.decred:
        prefix_hash = hash143.prefix_hash()

    for i_sign in range(tx.inputs_count):
        progress.advance()
        txi_sign = None
        key_sign = None
        key_sign_pub = None

        if segwit[i_sign]:
            # STAGE_REQUEST_SEGWIT_INPUT
            txi_sign = await helpers.request_tx_input(tx_req, i_sign)

            if not input_is_segwit(txi_sign):
                raise SigningError(
                    FailureType.ProcessError, "Transaction has changed during signing"
                )
            input_check_wallet_path(txi_sign, wallet_path)

            key_sign = keychain.derive(txi_sign.address_n, coin.curve_name)
            key_sign_pub = key_sign.public_key()
            txi_sign.script_sig = input_derive_script(coin, txi_sign, key_sign_pub)

            w_txi = writers.empty_bytearray(
                7 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4
            )
            if i_sign == 0:  # serializing first input => prepend headers
                writers.write_bytes(w_txi, get_tx_header(coin, tx, True))
            writers.write_tx_input(w_txi, txi_sign)
            tx_ser.serialized_tx = w_txi
            tx_ser.signature_index = None
            tx_ser.signature = None
            tx_req.serialized = tx_ser

        elif coin.force_bip143 or tx.overwintered:
            # STAGE_REQUEST_SEGWIT_INPUT
            txi_sign = await helpers.request_tx_input(tx_req, i_sign)
            input_check_wallet_path(txi_sign, wallet_path)

            is_bip143 = (
                txi_sign.script_type == InputScriptType.SPENDADDRESS
                or txi_sign.script_type == InputScriptType.SPENDMULTISIG
            )
            if not is_bip143 or txi_sign.amount > authorized_in:
                raise SigningError(
                    FailureType.ProcessError, "Transaction has changed during signing"
                )
            authorized_in -= txi_sign.amount

            key_sign = keychain.derive(txi_sign.address_n, coin.curve_name)
            key_sign_pub = key_sign.public_key()
            hash143_hash = hash143.preimage_hash(
                coin,
                tx,
                txi_sign,
                addresses.ecdsa_hash_pubkey(key_sign_pub, coin),
                get_hash_type(coin),
            )

            # if multisig, check if signing with a key that is included in multisig
            if txi_sign.multisig:
                multisig.multisig_pubkey_index(txi_sign.multisig, key_sign_pub)

            signature = ecdsa_sign(key_sign, hash143_hash)
            tx_ser.signature_index = i_sign
            tx_ser.signature = signature

            # serialize input with correct signature
            gc.collect()
            txi_sign.script_sig = input_derive_script(
                coin, txi_sign, key_sign_pub, signature
            )
            w_txi_sign = writers.empty_bytearray(
                5 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4
            )
            if i_sign == 0:  # serializing first input => prepend headers
                writers.write_bytes(w_txi_sign, get_tx_header(coin, tx))
            writers.write_tx_input(w_txi_sign, txi_sign)
            tx_ser.serialized_tx = w_txi_sign

            tx_req.serialized = tx_ser

        elif coin.decred:
            txi_sign = await helpers.request_tx_input(tx_req, i_sign)

            input_check_wallet_path(txi_sign, wallet_path)

            key_sign = keychain.derive(txi_sign.address_n, coin.curve_name)
            key_sign_pub = key_sign.public_key()

            if txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                prev_pkscript = scripts.output_script_multisig(
                    multisig.multisig_get_pubkeys(txi_sign.multisig),
                    txi_sign.multisig.m,
                )
            elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                prev_pkscript = scripts.output_script_p2pkh(
                    addresses.ecdsa_hash_pubkey(key_sign_pub, coin)
                )
            else:
                raise ValueError("Unknown input script type")

            h_witness = utils.HashWriter(blake256())
            writers.write_uint32(
                h_witness, tx.version | decred.DECRED_SERIALIZE_WITNESS_SIGNING
            )
            writers.write_varint(h_witness, tx.inputs_count)

            for ii in range(tx.inputs_count):
                if ii == i_sign:
                    writers.write_varint(h_witness, len(prev_pkscript))
                    writers.write_bytes(h_witness, prev_pkscript)
                else:
                    writers.write_varint(h_witness, 0)

            witness_hash = writers.get_tx_hash(
                h_witness, double=coin.sign_hash_double, reverse=False
            )

            h_sign = utils.HashWriter(blake256())
            writers.write_uint32(h_sign, decred.DECRED_SIGHASHALL)
            writers.write_bytes(h_sign, prefix_hash)
            writers.write_bytes(h_sign, witness_hash)

            sig_hash = writers.get_tx_hash(h_sign, double=coin.sign_hash_double)
            signature = ecdsa_sign(key_sign, sig_hash)
            tx_ser.signature_index = i_sign
            tx_ser.signature = signature

            # serialize input with correct signature
            gc.collect()
            txi_sign.script_sig = input_derive_script(
                coin, txi_sign, key_sign_pub, signature
            )
            w_txi_sign = writers.empty_bytearray(
                8 + 4 + len(hash143.get_last_output_bytes())
                if i_sign == 0
                else 0 + 16 + 4 + len(txi_sign.script_sig)
            )

            if i_sign == 0:
                writers.write_bytes(w_txi_sign, hash143.get_last_output_bytes())
                writers.write_uint32(w_txi_sign, tx.lock_time)
                writers.write_uint32(w_txi_sign, tx.expiry)
                writers.write_varint(w_txi_sign, tx.inputs_count)

            writers.write_tx_input_decred_witness(w_txi_sign, txi_sign)
            tx_ser.serialized_tx = w_txi_sign
            tx_req.serialized = tx_ser

        else:
            # hash of what we are signing with this input
            h_sign = utils.HashWriter(sha256())
            # same as h_first, checked before signing the digest
            h_second = utils.HashWriter(sha256())

            if tx.overwintered:
                writers.write_uint32(
                    h_sign, tx.version | zcash.OVERWINTERED
                )  # nVersion | fOverwintered
                writers.write_uint32(h_sign, tx.version_group_id)  # nVersionGroupId
            else:
                writers.write_uint32(h_sign, tx.version)  # nVersion
                if tx.timestamp:
                    writers.write_uint32(h_sign, tx.timestamp)

            writers.write_varint(h_sign, tx.inputs_count)

            for i in range(tx.inputs_count):
                # STAGE_REQUEST_4_INPUT
                txi = await helpers.request_tx_input(tx_req, i)
                input_check_wallet_path(txi, wallet_path)
                writers.write_tx_input_check(h_second, txi)
                if i == i_sign:
                    txi_sign = txi
                    key_sign = keychain.derive(txi.address_n, coin.curve_name)
                    key_sign_pub = key_sign.public_key()
                    # for the signing process the script_sig is equal
                    # to the previous tx's scriptPubKey (P2PKH) or a redeem script (P2SH)
                    if txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                        txi_sign.script_sig = scripts.output_script_multisig(
                            multisig.multisig_get_pubkeys(txi_sign.multisig),
                            txi_sign.multisig.m,
                        )
                    elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                        txi_sign.script_sig = scripts.output_script_p2pkh(
                            addresses.ecdsa_hash_pubkey(key_sign_pub, coin)
                        )
                        if coin.bip115:
                            txi_sign.script_sig += scripts.script_replay_protection_bip115(
                                txi_sign.prev_block_hash_bip115,
                                txi_sign.prev_block_height_bip115,
                            )
                    else:
                        raise SigningError(
                            FailureType.ProcessError, "Unknown transaction type"
                        )
                else:
                    txi.script_sig = bytes()
                writers.write_tx_input(h_sign, txi)

            writers.write_varint(h_sign, tx.outputs_count)

            for o in range(tx.outputs_count):
                # STAGE_REQUEST_4_OUTPUT
                txo = await helpers.request_tx_output(tx_req, o)
                txo_bin.amount = txo.amount
                txo_bin.script_pubkey = output_derive_script(txo, coin, keychain)
                writers.write_tx_output(h_second, txo_bin)
                writers.write_tx_output(h_sign, txo_bin)

            writers.write_uint32(h_sign, tx.lock_time)
            if tx.overwintered:
                writers.write_uint32(h_sign, tx.expiry)  # expiryHeight
                writers.write_varint(h_sign, 0)  # nJoinSplit

            writers.write_uint32(h_sign, get_hash_type(coin))

            # check the control digests
            if writers.get_tx_hash(h_first, False) != writers.get_tx_hash(h_second):
                raise SigningError(
                    FailureType.ProcessError, "Transaction has changed during signing"
                )

            # if multisig, check if signing with a key that is included in multisig
            if txi_sign.multisig:
                multisig.multisig_pubkey_index(txi_sign.multisig, key_sign_pub)

            # compute the signature from the tx digest
            signature = ecdsa_sign(
                key_sign, writers.get_tx_hash(h_sign, double=coin.sign_hash_double)
            )
            tx_ser.signature_index = i_sign
            tx_ser.signature = signature

            # serialize input with correct signature
            gc.collect()
            txi_sign.script_sig = input_derive_script(
                coin, txi_sign, key_sign_pub, signature
            )
            w_txi_sign = writers.empty_bytearray(
                5 + len(txi_sign.prev_hash) + 4 + len(txi_sign.script_sig) + 4
            )
            if i_sign == 0:  # serializing first input => prepend headers
                writers.write_bytes(w_txi_sign, get_tx_header(coin, tx))
            writers.write_tx_input(w_txi_sign, txi_sign)
            tx_ser.serialized_tx = w_txi_sign

            tx_req.serialized = tx_ser

    if coin.decred:
        return await helpers.request_tx_finish(tx_req)

    for o in range(tx.outputs_count):
        progress.advance()
        # STAGE_REQUEST_5_OUTPUT
        txo = await helpers.request_tx_output(tx_req, o)
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = output_derive_script(txo, coin, keychain)

        # serialize output
        w_txo_bin = writers.empty_bytearray(5 + 8 + 5 + len(txo_bin.script_pubkey) + 4)
        if o == 0:  # serializing first output => prepend outputs count
            writers.write_varint(w_txo_bin, tx.outputs_count)
        writers.write_tx_output(w_txo_bin, txo_bin)

        tx_ser.signature_index = None
        tx_ser.signature = None
        tx_ser.serialized_tx = w_txo_bin

        tx_req.serialized = tx_ser

    any_segwit = True in segwit.values()

    for i in range(tx.inputs_count):
        progress.advance()
        if segwit[i]:
            # STAGE_REQUEST_SEGWIT_WITNESS
            txi = await helpers.request_tx_input(tx_req, i)
            input_check_wallet_path(txi, wallet_path)

            if not input_is_segwit(txi) or txi.amount > authorized_in:
                raise SigningError(
                    FailureType.ProcessError, "Transaction has changed during signing"
                )
            authorized_in -= txi.amount

            key_sign = keychain.derive(txi.address_n, coin.curve_name)
            key_sign_pub = key_sign.public_key()
            hash143_hash = hash143.preimage_hash(
                coin,
                tx,
                txi,
                addresses.ecdsa_hash_pubkey(key_sign_pub, coin),
                get_hash_type(coin),
            )

            signature = ecdsa_sign(key_sign, hash143_hash)
            if txi.multisig:
                # find out place of our signature based on the pubkey
                signature_index = multisig.multisig_pubkey_index(
                    txi.multisig, key_sign_pub
                )
                witness = scripts.witness_p2wsh(
                    txi.multisig, signature, signature_index, get_hash_type(coin)
                )
            else:
                witness = scripts.witness_p2wpkh(
                    signature, key_sign_pub, get_hash_type(coin)
                )

            tx_ser.serialized_tx = witness
            tx_ser.signature_index = i
            tx_ser.signature = signature
        elif any_segwit:
            tx_ser.serialized_tx += bytearray(1)  # empty witness for non-segwit inputs
            tx_ser.signature_index = None
            tx_ser.signature = None

        tx_req.serialized = tx_ser

    writers.write_uint32(tx_ser.serialized_tx, tx.lock_time)

    if tx.overwintered:
        if tx.version == 3:
            writers.write_uint32(tx_ser.serialized_tx, tx.expiry)  # expiryHeight
            writers.write_varint(tx_ser.serialized_tx, 0)  # nJoinSplit
        elif tx.version == 4:
            writers.write_uint32(tx_ser.serialized_tx, tx.expiry)  # expiryHeight
            writers.write_uint64(tx_ser.serialized_tx, 0)  # valueBalance
            writers.write_varint(tx_ser.serialized_tx, 0)  # nShieldedSpend
            writers.write_varint(tx_ser.serialized_tx, 0)  # nShieldedOutput
            writers.write_varint(tx_ser.serialized_tx, 0)  # nJoinSplit
        else:
            raise SigningError(
                FailureType.DataError,
                "Unsupported version for overwintered transaction",
            )

    await helpers.request_tx_finish(tx_req)


async def get_prevtx_output_value(
    coin: coininfo.CoinInfo, tx_req: TxRequest, prev_hash: bytes, prev_index: int
) -> int:
    total_out = 0  # sum of output amounts

    # STAGE_REQUEST_2_PREV_META
    tx = await helpers.request_tx_meta(tx_req, prev_hash)

    if coin.decred:
        txh = utils.HashWriter(blake256())
    else:
        txh = utils.HashWriter(sha256())

    if tx.overwintered:
        writers.write_uint32(
            txh, tx.version | zcash.OVERWINTERED
        )  # nVersion | fOverwintered
        writers.write_uint32(txh, tx.version_group_id)  # nVersionGroupId
    elif coin.decred:
        writers.write_uint32(txh, tx.version | decred.DECRED_SERIALIZE_NO_WITNESS)
    else:
        writers.write_uint32(txh, tx.version)  # nVersion
        if tx.timestamp:
            writers.write_uint32(txh, tx.timestamp)

    writers.write_varint(txh, tx.inputs_cnt)

    for i in range(tx.inputs_cnt):
        # STAGE_REQUEST_2_PREV_INPUT
        txi = await helpers.request_tx_input(tx_req, i, prev_hash)
        if coin.decred:
            writers.write_tx_input_decred(txh, txi)
        else:
            writers.write_tx_input(txh, txi)

    writers.write_varint(txh, tx.outputs_cnt)

    for o in range(tx.outputs_cnt):
        # STAGE_REQUEST_2_PREV_OUTPUT
        txo_bin = await helpers.request_tx_output(tx_req, o, prev_hash)
        writers.write_tx_output(txh, txo_bin)
        if o == prev_index:
            total_out += txo_bin.amount
            if (
                coin.decred
                and txo_bin.decred_script_version is not None
                and txo_bin.decred_script_version != 0
            ):
                raise SigningError(
                    FailureType.ProcessError,
                    "Cannot use utxo that has script_version != 0",
                )

    writers.write_uint32(txh, tx.lock_time)

    if tx.overwintered or coin.decred:
        writers.write_uint32(txh, tx.expiry)

    ofs = 0
    while ofs < tx.extra_data_len:
        size = min(1024, tx.extra_data_len - ofs)
        data = await helpers.request_tx_extra_data(tx_req, ofs, size, prev_hash)
        writers.write_bytes(txh, data)
        ofs += len(data)

    if (
        writers.get_tx_hash(txh, double=coin.sign_hash_double, reverse=True)
        != prev_hash
    ):
        raise SigningError(FailureType.ProcessError, "Encountered invalid prev_hash")

    return total_out


# TX Helpers
# ===


def get_hash_type(coin: coininfo.CoinInfo) -> int:
    SIGHASH_FORKID = const(0x40)
    SIGHASH_ALL = const(0x01)
    hashtype = SIGHASH_ALL
    if coin.fork_id is not None:
        hashtype |= (coin.fork_id << 8) | SIGHASH_FORKID
    return hashtype


def get_tx_header(coin: coininfo.CoinInfo, tx: SignTx, segwit: bool = False):
    w_txi = bytearray()
    if tx.overwintered:
        writers.write_uint32(
            w_txi, tx.version | zcash.OVERWINTERED
        )  # nVersion | fOverwintered
        writers.write_uint32(w_txi, tx.version_group_id)  # nVersionGroupId
    else:
        writers.write_uint32(w_txi, tx.version)  # nVersion
        if tx.timestamp:
            writers.write_uint32(w_txi, tx.timestamp)
    if segwit:
        writers.write_varint(w_txi, 0x00)  # segwit witness marker
        writers.write_varint(w_txi, 0x01)  # segwit witness flag
    writers.write_varint(w_txi, tx.inputs_count)
    return w_txi


# TX Outputs
# ===


def output_derive_script(
    o: TxOutputType, coin: coininfo.CoinInfo, keychain: seed.Keychain
) -> bytes:

    if o.script_type == OutputScriptType.PAYTOOPRETURN:
        # op_return output
        if o.amount != 0:
            raise SigningError(
                FailureType.DataError, "OP_RETURN output with non-zero amount"
            )
        return scripts.output_script_paytoopreturn(o.op_return_data)

    if o.address_n:
        # change output
        if o.address:
            raise SigningError(FailureType.DataError, "Address in change output")
        o.address = get_address_for_change(o, coin, keychain)
    else:
        if not o.address:
            raise SigningError(FailureType.DataError, "Missing address")

    if coin.bech32_prefix and o.address.startswith(coin.bech32_prefix):
        # p2wpkh or p2wsh
        witprog = addresses.decode_bech32_address(coin.bech32_prefix, o.address)
        return scripts.output_script_native_p2wpkh_or_p2wsh(witprog)

    if coin.cashaddr_prefix is not None and o.address.startswith(
        coin.cashaddr_prefix + ":"
    ):
        prefix, addr = o.address.split(":")
        version, data = cashaddr.decode(prefix, addr)
        if version == cashaddr.ADDRESS_TYPE_P2KH:
            version = coin.address_type
        elif version == cashaddr.ADDRESS_TYPE_P2SH:
            version = coin.address_type_p2sh
        else:
            raise ValueError("Unknown cashaddr address type")
        raw_address = bytes([version]) + data
    else:
        raw_address = base58.decode_check(o.address, coin.b58_hash)

    if address_type.check(coin.address_type, raw_address):
        # p2pkh
        pubkeyhash = address_type.strip(coin.address_type, raw_address)
        script = scripts.output_script_p2pkh(pubkeyhash)
        if coin.bip115:
            script += scripts.script_replay_protection_bip115(
                o.block_hash_bip115, o.block_height_bip115
            )
        return script

    elif address_type.check(coin.address_type_p2sh, raw_address):
        # p2sh
        scripthash = address_type.strip(coin.address_type_p2sh, raw_address)
        script = scripts.output_script_p2sh(scripthash)
        if coin.bip115:
            script += scripts.script_replay_protection_bip115(
                o.block_hash_bip115, o.block_height_bip115
            )
        return script

    raise SigningError(FailureType.DataError, "Invalid address type")


def get_address_for_change(
    o: TxOutputType, coin: coininfo.CoinInfo, keychain: seed.Keychain
):
    if o.script_type == OutputScriptType.PAYTOADDRESS:
        input_script_type = InputScriptType.SPENDADDRESS
    elif o.script_type == OutputScriptType.PAYTOMULTISIG:
        input_script_type = InputScriptType.SPENDMULTISIG
    elif o.script_type == OutputScriptType.PAYTOWITNESS:
        input_script_type = InputScriptType.SPENDWITNESS
    elif o.script_type == OutputScriptType.PAYTOP2SHWITNESS:
        input_script_type = InputScriptType.SPENDP2SHWITNESS
    else:
        raise SigningError(FailureType.DataError, "Invalid script type")
    node = keychain.derive(o.address_n, coin.curve_name)
    return addresses.get_address(input_script_type, coin, node, o.multisig)


def output_is_change(
    o: TxOutputType,
    wallet_path: list,
    segwit_in: int,
    multifp: multisig.MultisigFingerprint,
) -> bool:
    if o.multisig and not multifp.matches(o.multisig):
        return False
    if output_is_segwit(o) and o.amount > segwit_in:
        # if the output is segwit, make sure it doesn't spend more than what the
        # segwit inputs paid.  this is to prevent user being tricked into
        # creating ANYONECANSPEND outputs before full segwit activation.
        return False
    return (
        wallet_path is not None
        and wallet_path == o.address_n[:-_BIP32_WALLET_DEPTH]
        and o.address_n[-2] <= _BIP32_CHANGE_CHAIN
        and o.address_n[-1] <= _BIP32_MAX_LAST_ELEMENT
    )


def output_is_segwit(o: TxOutputType) -> bool:
    return (
        o.script_type == OutputScriptType.PAYTOWITNESS
        or o.script_type == OutputScriptType.PAYTOP2SHWITNESS
    )


# Tx Inputs
# ===


def input_derive_script(
    coin: coininfo.CoinInfo, i: TxInputType, pubkey: bytes, signature: bytes = None
) -> bytes:
    if i.script_type == InputScriptType.SPENDADDRESS:
        # p2pkh or p2sh
        return scripts.input_script_p2pkh_or_p2sh(
            pubkey, signature, get_hash_type(coin)
        )

    if i.script_type == InputScriptType.SPENDP2SHWITNESS:
        # p2wpkh or p2wsh using p2sh

        if i.multisig:
            # p2wsh in p2sh
            pubkeys = multisig.multisig_get_pubkeys(i.multisig)
            witness_script_hasher = utils.HashWriter(sha256())
            scripts.output_script_multisig(pubkeys, i.multisig.m, witness_script_hasher)
            witness_script_hash = witness_script_hasher.get_digest()
            return scripts.input_script_p2wsh_in_p2sh(witness_script_hash)

        # p2wpkh in p2sh
        return scripts.input_script_p2wpkh_in_p2sh(
            addresses.ecdsa_hash_pubkey(pubkey, coin)
        )

    elif i.script_type == InputScriptType.SPENDWITNESS:
        # native p2wpkh or p2wsh
        return scripts.input_script_native_p2wpkh_or_p2wsh()

    elif i.script_type == InputScriptType.SPENDMULTISIG:
        # p2sh multisig
        signature_index = multisig.multisig_pubkey_index(i.multisig, pubkey)
        return scripts.input_script_multisig(
            i.multisig, signature, signature_index, get_hash_type(coin), coin
        )

    else:
        raise SigningError(FailureType.ProcessError, "Invalid script type")


def input_is_segwit(i: TxInputType) -> bool:
    return (
        i.script_type == InputScriptType.SPENDWITNESS
        or i.script_type == InputScriptType.SPENDP2SHWITNESS
    )


def input_extract_wallet_path(txi: TxInputType, wallet_path: list) -> list:
    if wallet_path is None:
        return None  # there was a mismatch in previous inputs
    address_n = txi.address_n[:-_BIP32_WALLET_DEPTH]
    if not address_n:
        return None  # input path is too short
    if not wallet_path:
        return address_n  # this is the first input
    if wallet_path == address_n:
        return address_n  # paths match
    return None  # paths don't match


def input_check_wallet_path(txi: TxInputType, wallet_path: list) -> list:
    if wallet_path is None:
        return  # there was a mismatch in Phase 1, ignore it now
    address_n = txi.address_n[:-_BIP32_WALLET_DEPTH]
    if wallet_path != address_n:
        raise SigningError(
            FailureType.ProcessError, "Transaction has changed during signing"
        )


def ecdsa_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder
