from typing import TYPE_CHECKING

from trezor.enums import TezosContractType
from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain
from apps.common.writers import write_bytes_fixed, write_uint8, write_uint32_be

from . import CURVE, PATTERNS, SLIP44_ID, helpers
from .helpers import (  # symbols used more than once
    CONTRACT_ID_SIZE,
    TAGGED_PUBKEY_HASH_SIZE,
    base58_encode_check,
    write_bool,
    write_instruction,
)

if TYPE_CHECKING:
    from trezor.messages import (
        TezosContractID,
        TezosDelegationOp,
        TezosOriginationOp,
        TezosRevealOp,
        TezosSignedTx,
        TezosSignTx,
        TezosTransactionOp,
    )
    from trezor.utils import Writer

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: TezosSignTx, keychain: Keychain) -> TezosSignedTx:
    from trezor.crypto import hashlib
    from trezor.crypto.curve import ed25519
    from trezor.enums import TezosBallotType
    from trezor.messages import TezosSignedTx

    from apps.common.paths import validate_path

    from . import layout

    await validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    transaction = msg.transaction  # local_cache_attribute
    origination = msg.origination  # local_cache_attribute
    delegation = msg.delegation  # local_cache_attribute

    if transaction is not None:
        fee = transaction.fee  # local_cache_attribute
        parameters_manager = transaction.parameters_manager  # local_cache_attribute

        # if the transaction operation is used to execute code on a smart contract
        if parameters_manager is not None:
            transfer = parameters_manager.transfer  # local_cache_attribute

            # operation to delegate from a smart contract with manager.tz
            if parameters_manager.set_delegate is not None:
                delegate = _get_address_by_tag(parameters_manager.set_delegate)
                await layout.require_confirm_delegation_baker(delegate)
                await layout.require_confirm_set_delegate(fee)

            # operation to remove delegate from the smart contract with manager.tz
            elif parameters_manager.cancel_delegate is not None:
                address = _get_address_from_contract(transaction.destination)
                await layout.require_confirm_delegation_manager_withdraw(address)
                await layout.require_confirm_manager_remove_delegate(fee)

            # operation to transfer tokens from a smart contract to an implicit account or a smart contract
            elif transfer is not None:
                to = _get_address_from_contract(transfer.destination)
                await layout.require_confirm_tx(
                    to, transfer.amount, chunkify=bool(msg.chunkify)
                )
                await layout.require_confirm_fee(transfer.amount, fee)
        else:
            # transactions from an implicit account
            to = _get_address_from_contract(transaction.destination)
            await layout.require_confirm_tx(
                to, transaction.amount, chunkify=bool(msg.chunkify)
            )
            await layout.require_confirm_fee(transaction.amount, fee)

    elif origination is not None:
        source = _get_address_by_tag(origination.source)
        await layout.require_confirm_origination(source)

        # if we are immediately delegating contract
        if origination.delegate is not None:
            delegate = _get_address_by_tag(origination.delegate)
            await layout.require_confirm_delegation_baker(delegate)

        await layout.require_confirm_origination_fee(
            origination.balance, origination.fee
        )

    elif delegation is not None:
        source = _get_address_by_tag(delegation.source)

        delegate_address: str | None = None
        if delegation.delegate is not None:
            delegate_address = _get_address_by_tag(delegation.delegate)

        if delegate_address is not None and source != delegate_address:
            await layout.require_confirm_delegation_baker(delegate_address)
            await layout.require_confirm_set_delegate(delegation.fee)
        # if account registers itself as a delegate
        else:
            await layout.require_confirm_register_delegate(source, delegation.fee)

    elif msg.proposal is not None:
        proposed_protocols = [
            # _get_protocol_hash
            base58_encode_check(p, "P")
            for p in msg.proposal.proposals
        ]
        await layout.require_confirm_proposals(proposed_protocols)

    elif msg.ballot is not None:
        # _get_protocol_hash
        proposed_protocol = base58_encode_check(msg.ballot.proposal, "P")

        # _get_ballot
        if msg.ballot.ballot == TezosBallotType.Yay:
            submitted_ballot = "yay"
        elif msg.ballot.ballot == TezosBallotType.Nay:
            submitted_ballot = "nay"
        elif msg.ballot.ballot == TezosBallotType.Pass:
            submitted_ballot = "pass"
        else:
            raise RuntimeError  # unrecognized enum value

        await layout.require_confirm_ballot(proposed_protocol, submitted_ballot)

    else:
        raise DataError("Invalid operation")

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
    ophash = base58_encode_check(sig_op_contents_hash, "o")

    sig_prefixed = base58_encode_check(signature, helpers.TEZOS_SIGNATURE_PREFIX)

    return TezosSignedTx(
        signature=sig_prefixed, sig_op_contents=sig_op_contents, operation_hash=ophash
    )


def _get_address_by_tag(address_hash: bytes) -> str:
    prefixes = ["tz1", "tz2", "tz3"]
    tag = int(address_hash[0])

    if 0 <= tag < len(prefixes):
        return base58_encode_check(address_hash[1:], prefixes[tag])
    raise DataError("Invalid tag in address hash")


def _get_address_from_contract(address: TezosContractID) -> str:
    if address.tag == TezosContractType.Implicit:
        return _get_address_by_tag(address.hash)

    elif address.tag == TezosContractType.Originated:
        return base58_encode_check(
            address.hash[:-1], helpers.TEZOS_ORIGINATED_ADDRESS_PREFIX
        )

    raise DataError("Invalid contract type")


def _get_operation_bytes(w: Writer, msg: TezosSignTx) -> None:
    from apps.common.writers import write_bytes_unchecked

    from .helpers import PROPOSAL_HASH_SIZE

    reveal = msg.reveal  # local_cache_attribute

    write_bytes_fixed(w, msg.branch, helpers.BRANCH_HASH_SIZE)

    # when the account sends first operation in lifetime,
    # we need to reveal its public key
    if reveal is not None:
        _encode_common(w, reveal, "reveal")
        tag = int(reveal.public_key[0])

        try:
            public_key_size = helpers.PUBLIC_KEY_TAG_TO_SIZE[tag]
        except KeyError:
            raise DataError("Invalid tag in public key")

        write_bytes_fixed(w, reveal.public_key, 1 + public_key_size)

    # transaction operation
    if msg.transaction is not None:
        transaction = msg.transaction
        _encode_common(w, transaction, "transaction")
        _encode_zarith(w, transaction.amount)

        # _encode_contract_id
        contract_id = transaction.destination
        write_uint8(w, contract_id.tag)
        write_bytes_fixed(w, contract_id.hash, CONTRACT_ID_SIZE - 1)

        # support delegation and transfer from the old scriptless contracts (now with manager.tz script)
        if transaction.parameters_manager is not None:
            parameters_manager = transaction.parameters_manager  # local_cache_attribute
            transfer = parameters_manager.transfer  # local_cache_attribute

            if parameters_manager.set_delegate is not None:
                # _encode_manager_delegation
                delegate = parameters_manager.set_delegate
                michelson_length = 42
                _encode_manager_common(w, michelson_length, "PUSH")
                write_bytes_fixed(w, delegate, TAGGED_PUBKEY_HASH_SIZE)
                for i in ("SOME", "SET_DELEGATE", "CONS"):
                    write_instruction(w, i)
            elif parameters_manager.cancel_delegate is not None:
                # _encode_manager_delegation_remove
                michelson_length = 14
                _encode_manager_common(w, michelson_length, "NONE")
                for i in ("SET_DELEGATE", "CONS"):
                    write_instruction(w, i)
            elif transfer is not None:
                assert transfer.destination is not None
                if transfer.destination.tag == TezosContractType.Implicit:
                    # _encode_manager_to_implicit_transfer
                    manager_transfer = transfer
                    michelson_length = 48
                    value_natural = bytearray()
                    _encode_natural(value_natural, manager_transfer.amount)
                    sequence_length = michelson_length + len(value_natural)

                    _encode_manager_common(w, sequence_length, "PUSH")
                    write_bytes_fixed(
                        w, manager_transfer.destination.hash, TAGGED_PUBKEY_HASH_SIZE
                    )
                    for i in ("IMPLICIT_ACCOUNT", "PUSH", "mutez"):
                        write_instruction(w, i)
                    _encode_natural(w, manager_transfer.amount)
                    for i in ("UNIT", "TRANSFER_TOKENS", "CONS"):
                        write_instruction(w, i)
                else:
                    # _encode_manager_to_manager_transfer
                    manager_transfer = transfer
                    michelson_length = 77

                    value_natural = bytearray()
                    _encode_natural(value_natural, manager_transfer.amount)
                    sequence_length = michelson_length + len(value_natural)

                    _encode_manager_common(w, sequence_length, "PUSH", to_contract=True)

                    # _encode_contract_id
                    contract_id = manager_transfer.destination
                    write_uint8(w, contract_id.tag)
                    write_bytes_fixed(w, contract_id.hash, CONTRACT_ID_SIZE - 1)

                    for i in ("CONTRACT", "unit", "ASSERT_SOME", "PUSH", "mutez"):
                        write_instruction(w, i)
                    _encode_natural(w, manager_transfer.amount)
                    for i in ("UNIT", "TRANSFER_TOKENS", "CONS"):
                        write_instruction(w, i)
        else:
            parameters = transaction.parameters  # local_cache_attribute
            if parameters:
                write_bool(w, True)
                helpers.check_tx_params_size(parameters)
                write_bytes_unchecked(w, parameters)
            else:
                write_bool(w, False)
    # origination operation
    elif msg.origination is not None:
        origination = msg.origination
        _encode_common(w, origination, "origination")
        _encode_zarith(w, origination.balance)
        _encode_data_with_bool_prefix(w, origination.delegate, TAGGED_PUBKEY_HASH_SIZE)
        helpers.check_script_size(origination.script)
        write_bytes_unchecked(w, origination.script)

    # delegation operation
    elif msg.delegation is not None:
        _encode_common(w, msg.delegation, "delegation")
        _encode_data_with_bool_prefix(
            w, msg.delegation.delegate, TAGGED_PUBKEY_HASH_SIZE
        )
    elif msg.proposal is not None:
        # _encode_proposal
        proposal = msg.proposal
        write_uint8(w, helpers.OP_TAG_PROPOSALS)
        write_bytes_fixed(w, proposal.source, TAGGED_PUBKEY_HASH_SIZE)
        write_uint32_be(w, proposal.period)
        write_uint32_be(w, len(proposal.proposals) * PROPOSAL_HASH_SIZE)
        for proposal_hash in proposal.proposals:
            write_bytes_fixed(w, proposal_hash, PROPOSAL_HASH_SIZE)
    elif msg.ballot is not None:
        # _encode_ballot
        ballot = msg.ballot
        write_uint8(w, helpers.OP_TAG_BALLOT)
        write_bytes_fixed(w, ballot.source, TAGGED_PUBKEY_HASH_SIZE)
        write_uint32_be(w, ballot.period)
        write_bytes_fixed(w, ballot.proposal, PROPOSAL_HASH_SIZE)
        write_uint8(w, ballot.ballot)


def _encode_common(
    w: Writer,
    operation: TezosDelegationOp
    | TezosOriginationOp
    | TezosTransactionOp
    | TezosRevealOp,
    str_operation: str,
) -> None:
    operation_tags = {
        "reveal": helpers.OP_TAG_REVEAL,
        "transaction": helpers.OP_TAG_TRANSACTION,
        "origination": helpers.OP_TAG_ORIGINATION,
        "delegation": helpers.OP_TAG_DELEGATION,
    }
    write_uint8(w, operation_tags[str_operation])
    write_bytes_fixed(w, operation.source, TAGGED_PUBKEY_HASH_SIZE)
    for num in (
        operation.fee,
        operation.counter,
        operation.gas_limit,
        operation.storage_limit,
    ):
        _encode_zarith(w, num)


def _encode_data_with_bool_prefix(
    w: Writer, data: bytes | None, expected_length: int
) -> None:
    if data:
        helpers.write_bool(w, True)
        write_bytes_fixed(w, data, expected_length)
    else:
        helpers.write_bool(w, False)


def _encode_zarith(w: Writer, num: int) -> None:
    while True:
        byte = num & 127
        num = num >> 7

        if num == 0:
            write_uint8(w, byte)
            break

        write_uint8(w, 128 | byte)


def _encode_natural(w: Writer, num: int) -> None:
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


def _encode_manager_common(
    w: Writer, sequence_length: int, operation: str, to_contract: bool = False
) -> None:
    # 5 = tag and sequence_length (1 byte + 4 bytes)
    argument_length = sequence_length + 5

    write_bool(w, True)
    write_uint8(w, helpers.DO_ENTRYPOINT_TAG)
    write_uint32_be(w, argument_length)
    write_uint8(w, helpers.MICHELSON_SEQUENCE_TAG)
    write_uint32_be(w, sequence_length)
    for i in ("DROP", "NIL", "operation", operation):
        write_instruction(w, i)
    if to_contract:
        write_instruction(w, "address")
    else:
        write_instruction(w, "key_hash")
    if operation == "PUSH":
        write_uint8(w, 10)  # byte sequence
        if to_contract:
            write_uint32_be(w, CONTRACT_ID_SIZE)
        else:
            write_uint32_be(w, TAGGED_PUBKEY_HASH_SIZE)
