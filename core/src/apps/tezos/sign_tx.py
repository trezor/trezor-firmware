from micropython import const

from trezor import wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import TezosBallotType, TezosContractType
from trezor.messages.TezosSignedTx import TezosSignedTx
from trezor.wire import errors

from apps.common import paths
from apps.common.writers import write_bytes, write_uint8, write_uint32_be
from apps.tezos import CURVE, helpers, layout

PROPOSAL_LENGTH = const(32)


async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)

    if msg.transaction is not None:
        to = _get_address_from_contract(msg.transaction.destination)
        await layout.require_confirm_tx(ctx, to, msg.transaction.amount)
        await layout.require_confirm_fee(
            ctx, msg.transaction.amount, msg.transaction.fee
        )

    elif msg.origination is not None:
        source = _get_address_from_contract(msg.origination.source)
        await layout.require_confirm_origination(ctx, source)

        # if we are immediately delegating contract
        if msg.origination.delegate is not None:
            delegate = _get_address_by_tag(msg.origination.delegate)
            await layout.require_confirm_delegation_baker(ctx, delegate)

        await layout.require_confirm_origination_fee(
            ctx, msg.origination.balance, msg.origination.fee
        )

    elif msg.delegation is not None:
        source = _get_address_from_contract(msg.delegation.source)

        delegate = None
        if msg.delegation.delegate is not None:
            delegate = _get_address_by_tag(msg.delegation.delegate)

        if delegate is not None and source != delegate:
            await layout.require_confirm_delegation_baker(ctx, delegate)
            await layout.require_confirm_set_delegate(ctx, msg.delegation.fee)
        # if account registers itself as a delegate
        else:
            await layout.require_confirm_register_delegate(
                ctx, source, msg.delegation.fee
            )

    elif msg.proposal is not None:
        proposed_protocols = [_get_protocol_hash(p) for p in msg.proposal.proposals]
        await layout.require_confirm_proposals(ctx, proposed_protocols)

    elif msg.ballot is not None:
        proposed_protocol = _get_protocol_hash(msg.ballot.proposal)
        submitted_ballot = _get_ballot(msg.ballot.ballot)
        await layout.require_confirm_ballot(ctx, proposed_protocol, submitted_ballot)

    else:
        raise errors.DataError("Invalid operation")

    w = bytearray()
    _get_operation_bytes(w, msg)

    opbytes = bytes(w)

    # watermark 0x03 is prefix for transactions, delegations, originations, reveals...
    watermark = bytes([3])
    wm_opbytes = watermark + opbytes
    wm_opbytes_hash = hashlib.blake2b(wm_opbytes, outlen=32).digest()

    signature = ed25519.sign(node.private_key(), wm_opbytes_hash)

    sig_op_contents = opbytes + signature
    sig_op_contents_hash = hashlib.blake2b(sig_op_contents, outlen=32).digest()
    ophash = helpers.base58_encode_check(sig_op_contents_hash, prefix="o")

    sig_prefixed = helpers.base58_encode_check(
        signature, prefix=helpers.TEZOS_SIGNATURE_PREFIX
    )

    return TezosSignedTx(
        signature=sig_prefixed, sig_op_contents=sig_op_contents, operation_hash=ophash
    )


def _get_address_by_tag(address_hash):
    prefixes = ["tz1", "tz2", "tz3"]
    tag = int(address_hash[0])

    if 0 <= tag < len(prefixes):
        return helpers.base58_encode_check(address_hash[1:], prefix=prefixes[tag])
    raise errors.DataError("Invalid tag in address hash")


def _get_address_from_contract(address):
    if address.tag == TezosContractType.Implicit:
        return _get_address_by_tag(address.hash)

    elif address.tag == TezosContractType.Originated:
        return helpers.base58_encode_check(
            address.hash[:-1], prefix=helpers.TEZOS_ORIGINATED_ADDRESS_PREFIX
        )

    raise errors.DataError("Invalid contract type")


def _get_protocol_hash(proposal):
    return helpers.base58_encode_check(proposal, prefix="P")


def _get_ballot(ballot):
    if ballot == TezosBallotType.Yay:
        return "yay"
    elif ballot == TezosBallotType.Nay:
        return "nay"
    elif ballot == TezosBallotType.Pass:
        return "pass"


def _get_operation_bytes(w: bytearray, msg):
    write_bytes(w, msg.branch)

    # when the account sends first operation in lifetime,
    # we need to reveal its public key
    if msg.reveal is not None:
        _encode_common(w, msg.reveal, "reveal")
        write_bytes(w, msg.reveal.public_key)

    # transaction operation
    if msg.transaction is not None:
        _encode_common(w, msg.transaction, "transaction")
        _encode_zarith(w, msg.transaction.amount)
        _encode_contract_id(w, msg.transaction.destination)
        _encode_data_with_bool_prefix(w, msg.transaction.parameters)
    # origination operation
    elif msg.origination is not None:
        _encode_common(w, msg.origination, "origination")
        write_bytes(w, msg.origination.manager_pubkey)
        _encode_zarith(w, msg.origination.balance)
        helpers.write_bool(w, msg.origination.spendable)
        helpers.write_bool(w, msg.origination.delegatable)
        _encode_data_with_bool_prefix(w, msg.origination.delegate)
        _encode_data_with_bool_prefix(w, msg.origination.script)
    # delegation operation
    elif msg.delegation is not None:
        _encode_common(w, msg.delegation, "delegation")
        _encode_data_with_bool_prefix(w, msg.delegation.delegate)
    elif msg.proposal is not None:
        _encode_proposal(w, msg.proposal)
    elif msg.ballot is not None:
        _encode_ballot(w, msg.ballot)


def _encode_common(w: bytearray, operation, str_operation):
    operation_tags = {"reveal": 7, "transaction": 8, "origination": 9, "delegation": 10}
    write_uint8(w, operation_tags[str_operation])
    _encode_contract_id(w, operation.source)
    _encode_zarith(w, operation.fee)
    _encode_zarith(w, operation.counter)
    _encode_zarith(w, operation.gas_limit)
    _encode_zarith(w, operation.storage_limit)


def _encode_contract_id(w: bytearray, contract_id):
    write_uint8(w, contract_id.tag)
    write_bytes(w, contract_id.hash)


def _encode_data_with_bool_prefix(w: bytearray, data):
    if data:
        helpers.write_bool(w, True)
        write_bytes(w, data)
    else:
        helpers.write_bool(w, False)


def _encode_zarith(w: bytearray, num):
    while True:
        byte = num & 127
        num = num >> 7

        if num == 0:
            write_uint8(w, byte)
            break

        write_uint8(w, 128 | byte)


def _encode_proposal(w: bytearray, proposal):
    proposal_tag = 5

    write_uint8(w, proposal_tag)
    write_bytes(w, proposal.source)
    write_uint32_be(w, proposal.period)
    write_uint32_be(w, len(proposal.proposals) * PROPOSAL_LENGTH)
    for proposal_hash in proposal.proposals:
        write_bytes(w, proposal_hash)


def _encode_ballot(w: bytearray, ballot):
    ballot_tag = 6

    write_uint8(w, ballot_tag)
    write_bytes(w, ballot.source)
    write_uint32_be(w, ballot.period)
    write_bytes(w, ballot.proposal)
    write_uint8(w, ballot.ballot)
