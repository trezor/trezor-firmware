from micropython import const

from trezor import wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import TezosBallotType, TezosContractType
from trezor.messages.TezosSignedTx import TezosSignedTx

from apps.common import paths
from apps.common.writers import write_bytes, write_uint8, write_uint32_be
from apps.tezos import CURVE, helpers, layout

PROPOSAL_LENGTH = const(32)
# support both the old (ATHENS) and the new protocol (BABYLON)
BABYLON_HASH = "PsBABY5HQTSkA4297zNHfsZNKtxULfL18y95qb3m53QJiXGmrbU"


async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)

    if msg.transaction is not None:
        if msg.transaction.kt_delegation:
            if msg.transaction.kt_delegation.delegate is not None:
                delegate = _get_address_by_tag(msg.transaction.kt_delegation.delegate)
                await layout.require_confirm_delegation_baker(ctx, delegate)
                await layout.require_confirm_set_delegate(ctx, msg.transaction.fee)
            else:
                address = _get_address_from_contract(msg.transaction.destination)
                await layout.require_confirm_delegation_kt_withdraw(ctx, address)
                await layout.require_confirm_set_delegate(ctx, msg.transaction.fee)
        elif msg.transaction.kt_transfer is not None:
            to = _get_address_by_tag(msg.transaction.kt_transfer.recipient)
            await layout.require_confirm_tx(ctx, to, msg.transaction.kt_transfer.amount)
            await layout.require_confirm_fee(
                ctx, msg.transaction.kt_transfer.amount, msg.transaction.fee
            )
        else:
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
        raise wire.DataError("Invalid operation")

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
    raise wire.DataError("Invalid tag in address hash")


def _get_address_from_contract(address):
    if address.tag == TezosContractType.Implicit:
        return _get_address_by_tag(address.hash)

    elif address.tag == TezosContractType.Originated:
        return helpers.base58_encode_check(
            address.hash[:-1], prefix=helpers.TEZOS_ORIGINATED_ADDRESS_PREFIX
        )

    raise wire.DataError("Invalid contract type")


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
        _encode_common(w, msg.reveal, "reveal", msg.protocol_hash)
        write_bytes(w, msg.reveal.public_key)

    # transaction operation
    if msg.transaction is not None:
        _encode_common(w, msg.transaction, "transaction", msg.protocol_hash)
        _encode_zarith(w, msg.transaction.amount)
        _encode_contract_id(w, msg.transaction.destination)
        # otocit
        if msg.protocol_hash == BABYLON_HASH:
            # support delegation from the old scriptless contracts (now with manager.tz script)
            if msg.transaction.kt_delegation is not None:
                if msg.transaction.kt_delegation.delegate is not None:
                    _encode_kt_delegation(w, msg.transaction.kt_delegation)
                else:
                    _encode_kt_delegation_remove(w, msg.transaction.kt_delegation)
            # support transfer of tokens from scriptless contracts (now with manager.tz script) to implicit accounts
            elif msg.transaction.kt_transfer is not None:
                _encode_kt_transfer(w, msg.transaction.kt_transfer)
            else:
                _encode_data_with_bool_prefix(w, msg.transaction.parameters)
        else:
            _encode_data_with_bool_prefix(w, msg.transaction.parameters)
    # origination operation
    elif msg.origination is not None:
        _encode_common(w, msg.origination, "origination", msg.protocol_hash)
        if msg.protocol_hash != BABYLON_HASH:
            write_bytes(w, msg.origination.manager_pubkey)
        _encode_zarith(w, msg.origination.balance)
        if msg.protocol_hash != BABYLON_HASH:
            helpers.write_bool(w, msg.origination.spendable)
            helpers.write_bool(w, msg.origination.delegatable)
        _encode_data_with_bool_prefix(w, msg.origination.delegate)
        if msg.protocol_hash != BABYLON_HASH:
            _encode_data_with_bool_prefix(w, msg.origination.script)
        else:
            write_bytes(w, msg.origination.script)

    # delegation operation
    elif msg.delegation is not None:
        _encode_common(w, msg.delegation, "delegation", msg.protocol_hash)
        _encode_data_with_bool_prefix(w, msg.delegation.delegate)
    elif msg.proposal is not None:
        _encode_proposal(w, msg.proposal)
    elif msg.ballot is not None:
        _encode_ballot(w, msg.ballot)


def _encode_common(w: bytearray, operation, str_operation, protocol):
    if protocol == BABYLON_HASH:
        operation_tags = {
            "reveal": 107,
            "transaction": 108,
            "origination": 109,
            "delegation": 110,
        }
    else:
        operation_tags = {
            "reveal": 7,
            "transaction": 8,
            "origination": 9,
            "delegation": 10,
        }
    write_uint8(w, operation_tags[str_operation])
    if protocol == BABYLON_HASH:
        write_bytes(w, operation.source.hash)
    else:
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


def _encode_natural(w: bytearray, num):
    # encode a natural integer with its signed bit on position 7
    # as we do not expect negative numbers in a transfer operation the bit is never set
    natural_tag = 0
    write_uint8(w, natural_tag)

    byte = num & 63
    modified = num >> 6

    if modified == 0:
        write_uint8(w, byte)
    else:
        write_uint8(w, 128 | byte)
        _encode_zarith(w, modified)


def _encode_kt_common(w: bytearray, sequence_length, operation):
    ADDRESS_LENGTH = 21

    argument_length = (
        sequence_length + 5
    )  # 5 = tag and sequence_length (1 byte + 4 bytes)

    helpers.write_bool(w, True)
    write_uint8(w, helpers.DO_ENTRYPOINT_TAG)
    write_uint32_be(w, argument_length)
    write_uint8(w, helpers.MICHELSON_SEQUENCE_TAG)
    write_uint32_be(w, sequence_length)
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["DROP"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["NIL"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["operation"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES[operation]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["key_hash"]))
    if operation == "PUSH":
        write_bytes(w, bytes([10]))  # byte sequence
        write_uint32_be(w, ADDRESS_LENGTH)


def _encode_kt_transfer(w: bytearray, kt_transfer):
    MICHELSON_LENGTH = 48

    value_natural = bytearray()
    _encode_natural(value_natural, kt_transfer.amount)
    sequence_length = MICHELSON_LENGTH + len(value_natural)

    _encode_kt_common(w, sequence_length, "PUSH")
    write_bytes(w, kt_transfer.recipient)
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["IMPLICIT_ACCOUNT"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["PUSH"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["mutez"]))
    _encode_natural(w, kt_transfer.amount)
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["UNIT"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["TRANSFER_TOKENS"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["CONS"]))


def _encode_kt_delegation(w: bytearray, kt_delegation):
    MICHELSON_LENGTH = 42  # length is fixed this time(no variable length fields)

    _encode_kt_common(w, MICHELSON_LENGTH, "PUSH")
    write_bytes(w, kt_delegation.delegate)
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["SOME"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["SET_DELEGATE"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["CONS"]))


def _encode_kt_delegation_remove(w: bytearray, kt_delegation):
    MICHELSON_LENGTH = 14  # length is fixed this time(no variable length fields)
    _encode_kt_common(w, MICHELSON_LENGTH, "NONE")
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["SET_DELEGATE"]))
    write_bytes(w, bytes(helpers.MICHELSON_INSTRUCTION_BYTES["CONS"]))
