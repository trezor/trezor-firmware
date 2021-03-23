from trezor import wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.enums import TezosBallotType, TezosContractType
from trezor.messages import TezosSignedTx

from apps.common import paths
from apps.common.keychain import with_slip44_keychain
from apps.common.writers import (
    write_bytes_fixed,
    write_bytes_unchecked,
    write_uint8,
    write_uint32_be,
)

from . import CURVE, PATTERNS, SLIP44_ID, helpers, layout


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)

    if msg.transaction is not None:
        # if the tranasction oprtation is used to execute code on a smart contract
        if msg.transaction.parameters_manager is not None:
            parameters_manager = msg.transaction.parameters_manager

            # operation to delegate from a smart contract with manager.tz
            if parameters_manager.set_delegate is not None:
                delegate = _get_address_by_tag(parameters_manager.set_delegate)
                await layout.require_confirm_delegation_baker(ctx, delegate)
                await layout.require_confirm_set_delegate(ctx, msg.transaction.fee)

            # operation to remove delegate from the smart contract with manager.tz
            elif parameters_manager.cancel_delegate is not None:
                address = _get_address_from_contract(msg.transaction.destination)
                await layout.require_confirm_delegation_manager_withdraw(ctx, address)
                await layout.require_confirm_manager_remove_delegate(
                    ctx, msg.transaction.fee
                )

            # operation to transfer tokens from a smart contract to an implicit account or a smart contract
            elif parameters_manager.transfer is not None:
                to = _get_address_from_contract(parameters_manager.transfer.destination)
                await layout.require_confirm_tx(
                    ctx, to, parameters_manager.transfer.amount
                )
                await layout.require_confirm_fee(
                    ctx, parameters_manager.transfer.amount, msg.transaction.fee
                )
        else:
            # transactions from an implicit account
            to = _get_address_from_contract(msg.transaction.destination)
            await layout.require_confirm_tx(ctx, to, msg.transaction.amount)
            await layout.require_confirm_fee(
                ctx, msg.transaction.amount, msg.transaction.fee
            )

    elif msg.origination is not None:
        source = _get_address_by_tag(msg.origination.source)
        await layout.require_confirm_origination(ctx, source)

        # if we are immediately delegating contract
        if msg.origination.delegate is not None:
            delegate = _get_address_by_tag(msg.origination.delegate)
            await layout.require_confirm_delegation_baker(ctx, delegate)

        await layout.require_confirm_origination_fee(
            ctx, msg.origination.balance, msg.origination.fee
        )

    elif msg.delegation is not None:
        source = _get_address_by_tag(msg.delegation.source)

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
    write_bytes_fixed(w, msg.branch, helpers.BRANCH_HASH_SIZE)

    # when the account sends first operation in lifetime,
    # we need to reveal its public key
    if msg.reveal is not None:
        _encode_common(w, msg.reveal, "reveal")
        tag = int(msg.reveal.public_key[0])

        try:
            public_key_size = helpers.PUBLIC_KEY_TAG_TO_SIZE[tag]
        except KeyError:
            raise wire.DataError("Invalid tag in public key")

        write_bytes_fixed(w, msg.reveal.public_key, 1 + public_key_size)

    # transaction operation
    if msg.transaction is not None:
        _encode_common(w, msg.transaction, "transaction")
        _encode_zarith(w, msg.transaction.amount)
        _encode_contract_id(w, msg.transaction.destination)

        # support delegation and transfer from the old scriptless contracts (now with manager.tz script)
        if msg.transaction.parameters_manager is not None:
            parameters_manager = msg.transaction.parameters_manager

            if parameters_manager.set_delegate is not None:
                _encode_manager_delegation(w, parameters_manager.set_delegate)
            elif parameters_manager.cancel_delegate is not None:
                _encode_manager_delegation_remove(w)
            elif parameters_manager.transfer is not None:
                if (
                    parameters_manager.transfer.destination.tag
                    == TezosContractType.Implicit
                ):
                    _encode_manager_to_implicit_transfer(w, parameters_manager.transfer)
                else:
                    _encode_manager_to_manager_transfer(w, parameters_manager.transfer)
        else:
            if msg.transaction.parameters:
                helpers.write_bool(w, True)
                helpers.check_tx_params_size(msg.transaction.parameters)
                write_bytes_unchecked(w, msg.transaction.parameters)
            else:
                helpers.write_bool(w, False)
    # origination operation
    elif msg.origination is not None:
        _encode_common(w, msg.origination, "origination")
        _encode_zarith(w, msg.origination.balance)
        _encode_data_with_bool_prefix(
            w, msg.origination.delegate, helpers.TAGGED_PUBKEY_HASH_SIZE
        )
        helpers.check_script_size(msg.origination.script)
        write_bytes_unchecked(w, msg.origination.script)

    # delegation operation
    elif msg.delegation is not None:
        _encode_common(w, msg.delegation, "delegation")
        _encode_data_with_bool_prefix(
            w, msg.delegation.delegate, helpers.TAGGED_PUBKEY_HASH_SIZE
        )
    elif msg.proposal is not None:
        _encode_proposal(w, msg.proposal)
    elif msg.ballot is not None:
        _encode_ballot(w, msg.ballot)


def _encode_common(w: bytearray, operation, str_operation):
    operation_tags = {
        "reveal": helpers.OP_TAG_REVEAL,
        "transaction": helpers.OP_TAG_TRANSACTION,
        "origination": helpers.OP_TAG_ORIGINATION,
        "delegation": helpers.OP_TAG_DELEGATION,
    }
    write_uint8(w, operation_tags[str_operation])
    write_bytes_fixed(w, operation.source, helpers.TAGGED_PUBKEY_HASH_SIZE)
    _encode_zarith(w, operation.fee)
    _encode_zarith(w, operation.counter)
    _encode_zarith(w, operation.gas_limit)
    _encode_zarith(w, operation.storage_limit)


def _encode_contract_id(w: bytearray, contract_id):
    write_uint8(w, contract_id.tag)
    write_bytes_fixed(w, contract_id.hash, helpers.CONTRACT_ID_SIZE - 1)


def _encode_data_with_bool_prefix(w: bytearray, data: bytes, expected_length: int):
    if data:
        helpers.write_bool(w, True)
        write_bytes_fixed(w, data, expected_length)
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
    write_uint8(w, helpers.OP_TAG_PROPOSALS)
    write_bytes_fixed(w, proposal.source, helpers.TAGGED_PUBKEY_HASH_SIZE)
    write_uint32_be(w, proposal.period)
    write_uint32_be(w, len(proposal.proposals) * helpers.PROPOSAL_HASH_SIZE)
    for proposal_hash in proposal.proposals:
        write_bytes_fixed(w, proposal_hash, helpers.PROPOSAL_HASH_SIZE)


def _encode_ballot(w: bytearray, ballot):
    write_uint8(w, helpers.OP_TAG_BALLOT)
    write_bytes_fixed(w, ballot.source, helpers.TAGGED_PUBKEY_HASH_SIZE)
    write_uint32_be(w, ballot.period)
    write_bytes_fixed(w, ballot.proposal, helpers.PROPOSAL_HASH_SIZE)
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


def _encode_manager_common(w: bytearray, sequence_length, operation, to_contract=False):
    # 5 = tag and sequence_length (1 byte + 4 bytes)
    argument_length = sequence_length + 5

    helpers.write_bool(w, True)
    write_uint8(w, helpers.DO_ENTRYPOINT_TAG)
    write_uint32_be(w, argument_length)
    write_uint8(w, helpers.MICHELSON_SEQUENCE_TAG)
    write_uint32_be(w, sequence_length)
    helpers.write_instruction(w, "DROP")
    helpers.write_instruction(w, "NIL")
    helpers.write_instruction(w, "operation")
    helpers.write_instruction(w, operation)
    if to_contract is True:
        helpers.write_instruction(w, "address")
    else:
        helpers.write_instruction(w, "key_hash")
    if operation == "PUSH":
        write_uint8(w, 10)  # byte sequence
        if to_contract is True:
            write_uint32_be(w, helpers.CONTRACT_ID_SIZE)
        else:
            write_uint32_be(w, helpers.TAGGED_PUBKEY_HASH_SIZE)


def _encode_manager_to_implicit_transfer(w: bytearray, manager_transfer):
    MICHELSON_LENGTH = 48

    value_natural = bytearray()
    _encode_natural(value_natural, manager_transfer.amount)
    sequence_length = MICHELSON_LENGTH + len(value_natural)

    _encode_manager_common(w, sequence_length, "PUSH")
    write_bytes_fixed(
        w, manager_transfer.destination.hash, helpers.TAGGED_PUBKEY_HASH_SIZE
    )
    helpers.write_instruction(w, "IMPLICIT_ACCOUNT")
    helpers.write_instruction(w, "PUSH")
    helpers.write_instruction(w, "mutez")
    _encode_natural(w, manager_transfer.amount)
    helpers.write_instruction(w, "UNIT")
    helpers.write_instruction(w, "TRANSFER_TOKENS")
    helpers.write_instruction(w, "CONS")


# smart_contract_delegation
def _encode_manager_delegation(w: bytearray, delegate):
    MICHELSON_LENGTH = 42  # length is fixed this time(no variable length fields)

    _encode_manager_common(w, MICHELSON_LENGTH, "PUSH")
    write_bytes_fixed(w, delegate, helpers.TAGGED_PUBKEY_HASH_SIZE)
    helpers.write_instruction(w, "SOME")
    helpers.write_instruction(w, "SET_DELEGATE")
    helpers.write_instruction(w, "CONS")


def _encode_manager_delegation_remove(w: bytearray):
    MICHELSON_LENGTH = 14  # length is fixed this time(no variable length fields)
    _encode_manager_common(w, MICHELSON_LENGTH, "NONE")
    helpers.write_instruction(w, "SET_DELEGATE")
    helpers.write_instruction(w, "CONS")


def _encode_manager_to_manager_transfer(w: bytearray, manager_transfer):
    MICHELSON_LENGTH = 77

    value_natural = bytearray()
    _encode_natural(value_natural, manager_transfer.amount)
    sequence_length = MICHELSON_LENGTH + len(value_natural)

    _encode_manager_common(w, sequence_length, "PUSH", to_contract=True)
    _encode_contract_id(w, manager_transfer.destination)
    helpers.write_instruction(w, "CONTRACT")
    helpers.write_instruction(w, "unit")
    helpers.write_instruction(w, "ASSERT_SOME")
    helpers.write_instruction(w, "PUSH")
    helpers.write_instruction(w, "mutez")
    _encode_natural(w, manager_transfer.amount)
    helpers.write_instruction(w, "UNIT")
    helpers.write_instruction(w, "TRANSFER_TOKENS")
    helpers.write_instruction(w, "CONS")
