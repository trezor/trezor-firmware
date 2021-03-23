"""
Initializes a new transaction.
"""

import gc

from apps.monero import misc, signing
from apps.monero.layout import confirms
from apps.monero.signing.state import State
from apps.monero.xmr import crypto, monero

if False:
    from apps.monero.xmr.types import Sc25519, Ge25519
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
        MoneroTransactionInitAck,
        MoneroTransactionRsigData,
    )


async def init_transaction(
    state: State,
    address_n: list,
    network_type: int,
    tsx_data: MoneroTransactionData,
    keychain,
) -> MoneroTransactionInitAck:
    from apps.monero.signing import offloading_keys
    from apps.common import paths

    await paths.validate_path(state.ctx, keychain, address_n)

    state.creds = misc.get_creds(keychain, address_n, network_type)
    state.client_version = tsx_data.client_version or 0
    if state.client_version == 0:
        raise ValueError("Client version not supported")

    state.fee = state.fee if state.fee > 0 else 0
    state.tx_priv = crypto.random_scalar()
    state.tx_pub = crypto.scalarmult_base(state.tx_priv)
    state.mem_trace(1)

    state.input_count = tsx_data.num_inputs
    state.output_count = len(tsx_data.outputs)
    state.progress_total = 4 + 3 * state.input_count + state.output_count
    state.progress_cur = 0

    # Ask for confirmation
    await confirms.require_confirm_transaction(
        state.ctx, state, tsx_data, state.creds.network_type
    )
    state.creds.address = None
    state.creds.network_type = None
    gc.collect()
    state.mem_trace(3)

    # Basic transaction parameters
    state.output_change = tsx_data.change_dts
    state.mixin = tsx_data.mixin
    state.fee = tsx_data.fee
    state.account_idx = tsx_data.account
    state.last_step = state.STEP_INIT
    if tsx_data.hard_fork:
        state.hard_fork = tsx_data.hard_fork

    state.tx_type = (
        signing.RctType.CLSAG if state.hard_fork >= 13 else signing.RctType.Bulletproof2
    )

    # Ensure change is correct
    _check_change(state, tsx_data.outputs)

    # At least two outpus are required, this applies also for sweep txs
    # where one fake output is added. See _check_change for more info
    if state.output_count < 2:
        raise signing.NotEnoughOutputsError("At least two outputs are required")

    _check_rsig_data(state, tsx_data.rsig_data)
    _check_subaddresses(state, tsx_data.outputs)

    # Extra processing, payment id
    _process_payment_id(state, tsx_data)
    _compute_sec_keys(state, tsx_data)
    gc.collect()

    # Iterative tx_prefix_hash hash computation
    state.tx_prefix_hasher.uvarint(2)  # current Monero transaction format (RingCT = 2)
    state.tx_prefix_hasher.uvarint(tsx_data.unlock_time)
    state.tx_prefix_hasher.uvarint(state.input_count)  # ContainerType, size
    state.mem_trace(10, True)

    # Final message hasher
    state.full_message_hasher.init()
    state.full_message_hasher.set_type_fee(state.tx_type, state.fee)

    # Sub address precomputation
    if tsx_data.account is not None and tsx_data.minor_indices:
        _precompute_subaddr(state, tsx_data.account, tsx_data.minor_indices)
    state.mem_trace(5, True)

    # HMACs all outputs to disallow tampering.
    # Each HMAC is then sent alongside the output
    # and trezor validates it.
    hmacs = []
    for idx in range(state.output_count):
        c_hmac = offloading_keys.gen_hmac_tsxdest(
            state.key_hmac, tsx_data.outputs[idx], idx
        )
        hmacs.append(c_hmac)
        gc.collect()

    state.mem_trace(6)

    from trezor.messages import (
        MoneroTransactionInitAck,
        MoneroTransactionRsigData,
    )

    rsig_data = MoneroTransactionRsigData(offload_type=int(state.rsig_offload))

    return MoneroTransactionInitAck(hmacs=hmacs, rsig_data=rsig_data)


def _check_subaddresses(state: State, outputs: list[MoneroTransactionDestinationEntry]):
    """
    Using subaddresses leads to a few poorly documented exceptions.

    Normally we set R=r*G (tx_pub), however for subaddresses this is equal to R=r*D
    to achieve the nice blockchain scanning property.

    Remember, that R is per-transaction and not per-input. It's all good if we have a
    single output or we have a single destination and the second output is our change.
    This is because although the R=r*D, we can still derive the change using our private view-key.
    In other words, calculate the one-time address as P = H(x*R)*G + Y (where X,Y is the change).

    However, this does not work for other outputs than change, because we do not have the
    recipient's view key, so we cannot use the same formula -- we need a new R.

    The solution is very straightforward -- we create additional `R`s and use the `extra`
    field to include them under the `ADDITIONAL_PUBKEYS` tag.

    See:
    - https://lab.getmonero.org/pubs/MRL-0006.pdf
    - https://github.com/monero-project/monero/pull/2056
    """
    from apps.monero.xmr.addresses import classify_subaddresses

    # let's first figure out what kind of destinations we have
    num_stdaddresses, num_subaddresses, single_dest_subaddress = classify_subaddresses(
        outputs, state.change_address()
    )

    # if this is a single-destination transfer to a subaddress,
    # we set (override) the tx pubkey to R=r*D and no additional
    # tx keys are needed
    if num_stdaddresses == 0 and num_subaddresses == 1:
        state.tx_pub = crypto.scalarmult(
            crypto.decodepoint(single_dest_subaddress.spend_public_key), state.tx_priv
        )

    # if a subaddress is used and either standard address is as well
    # or more than one subaddress is used we need to add additional tx keys
    state.need_additional_txkeys = num_subaddresses > 0 and (
        num_stdaddresses > 0 or num_subaddresses > 1
    )
    state.mem_trace(4, True)


def _get_primary_change_address(state: State) -> MoneroAccountPublicAddress:
    """
    Computes primary change address for the current account index
    """
    from trezor.messages import MoneroAccountPublicAddress

    D, C = monero.generate_sub_address_keys(
        state.creds.view_key_private, state.creds.spend_key_public, state.account_idx, 0
    )
    return MoneroAccountPublicAddress(
        view_public_key=crypto.encodepoint(C), spend_public_key=crypto.encodepoint(D)
    )


def _check_rsig_data(state: State, rsig_data: MoneroTransactionRsigData):
    """
    There are two types of monero ring confidential transactions:
    1. RCTTypeFull = 1 (used if num_inputs == 1 && Borromean)
    2. RCTTypeSimple = 2 (for num_inputs > 1 || !Borromean)

    and four types of range proofs (set in `rsig_data.rsig_type`):
    1. RangeProofBorromean = 0
    2. RangeProofBulletproof = 1
    3. RangeProofMultiOutputBulletproof = 2
    4. RangeProofPaddedBulletproof = 3

    The current code supports only HF9, HF10 thus TX type is always simple
    and RCT algorithm is always Bulletproof.
    """
    state.rsig_grouping = rsig_data.grouping

    if rsig_data.rsig_type == 0:
        raise ValueError("Borromean range sig not supported")

    elif rsig_data.rsig_type not in (1, 2, 3):
        raise ValueError("Unknown rsig type")

    if state.output_count > 2:
        state.rsig_offload = True

    _check_grouping(state)


def _check_grouping(state: State):
    acc = 0
    for x in state.rsig_grouping:
        if x is None or x <= 0:
            raise ValueError("Invalid grouping batch")
        acc += x

    if acc != state.output_count:
        raise ValueError("Invalid grouping")


def _check_change(state: State, outputs: list[MoneroTransactionDestinationEntry]):
    """
    Check if the change address in state.output_change (from `tsx_data.outputs`) is
    a) among tx outputs
    b) is equal to our address

    The change output is in `tsx_data.change_dts`, but also has to be in `tsx_data.outputs`.
    This is what Monero does in its cold wallet signing protocol.

    In other words, these structures are built by Monero when generating unsigned transaction set
    and we do not want to modify this logic. We just translate the unsigned tx to the protobuf message.

    So, although we could probably optimize this by having the change output in `change_dts`
    only, we intentionally do not do so.
    """
    from apps.monero.xmr.addresses import addr_eq, get_change_addr_idx

    change_index = get_change_addr_idx(outputs, state.output_change)

    change_addr = state.change_address()
    # if there is no change, there is nothing to check
    if change_addr is None:
        state.mem_trace("No change" if __debug__ else None)
        return

    """
    Sweep tx is just one output and no change.
    To prevent recognition of such transactions another fake output is added
    that spends exactly 0 coins to a random address.
    See https://github.com/monero-project/monero/pull/1415
    """
    if change_index is None and state.output_change.amount == 0 and len(outputs) == 2:
        state.mem_trace("Sweep tsx" if __debug__ else None)
        return

    found = False
    for out in outputs:
        if addr_eq(out.addr, change_addr):
            found = True
            break

    if not found:
        raise signing.ChangeAddressError("Change address not found in outputs")

    my_addr = _get_primary_change_address(state)
    if not addr_eq(my_addr, change_addr):
        raise signing.ChangeAddressError("Change address differs from ours")


def _compute_sec_keys(state: State, tsx_data: MoneroTransactionData):
    """
    Generate master key H( H(TsxData || tx_priv) || rand )
    """
    from trezor import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    writer = get_keccak_writer()
    writer.write(protobuf.dump_message_buffer(tsx_data))
    writer.write(crypto.encodeint(state.tx_priv))

    master_key = crypto.keccak_2hash(
        writer.get_digest() + crypto.encodeint(crypto.random_scalar())
    )
    state.key_hmac = crypto.keccak_2hash(b"hmac" + master_key)
    state.key_enc = crypto.keccak_2hash(b"enc" + master_key)


def _precompute_subaddr(state: State, account: int, indices: list[int]):
    """
    Precomputes subaddresses for account (major) and list of indices (minors)
    Subaddresses have to be stored in encoded form - unique representation.
    Single point can have multiple extended coordinates representation - would not match during subaddress search.
    """
    monero.compute_subaddresses(state.creds, account, indices, state.subaddresses)


def _process_payment_id(state: State, tsx_data: MoneroTransactionData):
    """
    Writes payment id to the `extra` field under the TX_EXTRA_NONCE = 0x02 tag.

    The second tag describes if the payment id is encrypted or not.
    If the payment id is 8 bytes long it implies encryption and
    therefore the TX_EXTRA_NONCE_ENCRYPTED_PAYMENT_ID = 0x01 tag is used.
    If it is not encrypted, we use TX_EXTRA_NONCE_PAYMENT_ID = 0x00.

    Since Monero release 0.13 all 2 output payments have encrypted payment ID
    to make BC more uniform.

    See:
    - https://github.com/monero-project/monero/blob/ff7dc087ae5f7de162131cea9dbcf8eac7c126a1/src/cryptonote_basic/tx_extra.h
    """
    # encrypted payment id / dummy payment ID
    view_key_pub_enc = None

    if not tsx_data.payment_id or len(tsx_data.payment_id) == 8:
        view_key_pub_enc = _get_key_for_payment_id_encryption(
            tsx_data, state.change_address(), state.client_version > 0
        )

    if not tsx_data.payment_id:
        return

    elif len(tsx_data.payment_id) == 8:
        view_key_pub = crypto.decodepoint(view_key_pub_enc)
        payment_id_encr = _encrypt_payment_id(
            tsx_data.payment_id, view_key_pub, state.tx_priv
        )

        extra_nonce = payment_id_encr
        extra_prefix = 1  # TX_EXTRA_NONCE_ENCRYPTED_PAYMENT_ID

    # plain text payment id
    elif len(tsx_data.payment_id) == 32:
        extra_nonce = tsx_data.payment_id
        extra_prefix = 0  # TX_EXTRA_NONCE_PAYMENT_ID

    else:
        raise ValueError("Payment ID size invalid")

    lextra = len(extra_nonce)
    if lextra >= 255:
        raise ValueError("Nonce could be 255 bytes max")

    # write it to extra
    extra_buff = bytearray(3 + lextra)
    extra_buff[0] = 2  # TX_EXTRA_NONCE
    extra_buff[1] = lextra + 1
    extra_buff[2] = extra_prefix
    extra_buff[3:] = extra_nonce
    state.extra_nonce = extra_buff


def _get_key_for_payment_id_encryption(
    tsx_data: MoneroTransactionData,
    change_addr=None,
    add_dummy_payment_id: bool = False,
) -> bytes:
    """
    Returns destination address public view key to be used for
    payment id encryption. If no encrypted payment ID is chosen,
    dummy payment ID is set for better transaction uniformity if possible.
    """
    from apps.monero.xmr.addresses import addr_eq
    from trezor.messages import MoneroAccountPublicAddress

    addr = MoneroAccountPublicAddress(
        spend_public_key=crypto.NULL_KEY_ENC, view_public_key=crypto.NULL_KEY_ENC
    )
    count = 0
    for dest in tsx_data.outputs:
        if dest.amount == 0:
            continue
        if change_addr and addr_eq(dest.addr, change_addr):
            continue
        if addr_eq(dest.addr, addr):
            continue
        if count > 0 and tsx_data.payment_id:
            raise ValueError(
                "Destinations have to have exactly one output to support encrypted payment ids"
            )
        addr = dest.addr
        count += 1

    # Insert dummy payment id for transaction uniformity
    if not tsx_data.payment_id and count <= 1 and add_dummy_payment_id:
        tsx_data.payment_id = bytearray(8)

    if count == 0 and change_addr:
        return change_addr.view_public_key

    if addr.view_public_key == crypto.NULL_KEY_ENC:
        raise ValueError("Invalid key")

    return addr.view_public_key


def _encrypt_payment_id(
    payment_id: bytes, public_key: Ge25519, secret_key: Sc25519
) -> bytes:
    """
    Encrypts payment_id hex.
    Used in the transaction extra. Only recipient is able to decrypt.
    """
    derivation_p = crypto.generate_key_derivation(public_key, secret_key)
    derivation = bytearray(33)
    derivation = crypto.encodepoint_into(derivation, derivation_p)
    derivation[32] = 0x8D  # ENCRYPTED_PAYMENT_ID_TAIL
    hash = crypto.cn_fast_hash(derivation)
    pm_copy = bytearray(payment_id)
    return crypto.xor8(pm_copy, hash)
