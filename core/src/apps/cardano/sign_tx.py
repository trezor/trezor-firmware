from micropython import const

from trezor import log, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import CardanoAddressType, CardanoCertificateType
from trezor.messages.CardanoAddressParametersType import CardanoAddressParametersType
from trezor.messages.CardanoSignedTx import CardanoSignedTx

from apps.common import cbor
from apps.common.paths import validate_path
from apps.common.seed import remove_ed25519_prefix

from . import CURVE, seed
from .address import (
    derive_address_bytes,
    derive_human_readable_address,
    get_address_bytes_unsafe,
    get_public_key_hash,
    is_staking_path,
    validate_full_path,
    validate_output_address,
)
from .byron_address import get_address_attributes
from .helpers import (
    INVALID_CERTIFICATE,
    INVALID_METADATA,
    INVALID_WITHDRAWAL,
    network_ids,
    protocol_magics,
    staking_use_cases,
)
from .helpers.utils import to_account_path
from .layout import (
    confirm_certificate,
    confirm_sending,
    confirm_transaction,
    confirm_withdrawal,
    show_warning_tx_different_staking_account,
    show_warning_tx_no_staking_info,
    show_warning_tx_pointer_address,
    show_warning_tx_staking_key_hash,
)
from .seed import is_byron_path, is_shelley_path

if False:
    from typing import Dict, List, Tuple
    from trezor.messages.CardanoSignTx import CardanoSignTx
    from trezor.messages.CardanoTxInputType import CardanoTxInputType
    from trezor.messages.CardanoTxOutputType import CardanoTxOutputType
    from trezor.messages.CardanoTxCertificateType import CardanoTxCertificateType
    from trezor.messages.CardanoTxWithdrawalType import CardanoTxWithdrawalType

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
MAX_CHANGE_ADDRESS_INDEX = const(1000000)
ACCOUNT_PATH_INDEX = const(2)
BIP_PATH_LENGTH = const(5)

LOVELACE_MAX_SUPPLY = 45_000_000_000 * 1_000_000

POOL_HASH_SIZE = 28
METADATA_HASH_SIZE = 32
MAX_METADATA_LENGTH = 500


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTx, keychain: seed.Keychain
) -> CardanoSignedTx:
    try:
        if msg.fee > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Fee is out of range!")

        _validate_network_info(msg.network_id, msg.protocol_magic)

        for i in msg.inputs:
            await validate_path(ctx, validate_full_path, keychain, i.address_n, CURVE)

        _validate_outputs(keychain, msg.outputs, msg.protocol_magic, msg.network_id)
        _validate_certificates(msg.certificates)
        _validate_withdrawals(msg.withdrawals)
        _validate_metadata(msg.metadata)

        # display the transaction in UI
        await _show_tx(ctx, keychain, msg)

        # sign the transaction bundle and prepare the result
        serialized_tx, tx_hash = _serialize_tx(keychain, msg)
        tx = CardanoSignedTx(serialized_tx=serialized_tx, tx_hash=tx_hash)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    return tx


def _validate_network_info(network_id: int, protocol_magic: int) -> None:
    """
    We are only concerned about checking that both network_id and protocol_magic
    belong to the mainnet or that both belong to a testnet. We don't need to check for
    consistency between various testnets (at least for now).
    """
    is_mainnet_network_id = network_ids.is_mainnet(network_id)
    is_mainnet_protocol_magic = protocol_magics.is_mainnet(protocol_magic)

    if is_mainnet_network_id != is_mainnet_protocol_magic:
        raise wire.ProcessError("Invalid network id/protocol magic combination!")


def _validate_outputs(
    keychain: seed.Keychain,
    outputs: List[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> None:
    if not outputs:
        raise wire.ProcessError("Transaction has no outputs!")

    total_amount = 0
    for output in outputs:
        total_amount += output.amount
        if output.address_parameters:
            # try to derive the address to validate it
            derive_address_bytes(
                keychain, output.address_parameters, protocol_magic, network_id
            )
        elif output.address is not None:
            validate_output_address(output.address, protocol_magic, network_id)
        else:
            raise wire.ProcessError(
                "Each output must have an address field or address_parameters!"
            )

    if total_amount > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Total transaction amount is out of range!")


def _validate_certificates(certificates: List[CardanoTxCertificateType]) -> None:
    for certificate in certificates:
        if not is_staking_path(certificate.path):
            raise INVALID_CERTIFICATE

        if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
            if certificate.pool is None or len(certificate.pool) != POOL_HASH_SIZE:
                raise INVALID_CERTIFICATE


def _validate_withdrawals(withdrawals: List[CardanoTxWithdrawalType]) -> None:
    for withdrawal in withdrawals:
        if not is_staking_path(withdrawal.path):
            raise INVALID_WITHDRAWAL

        if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
            raise INVALID_WITHDRAWAL


def _validate_metadata(metadata: bytes) -> None:
    if not metadata:
        return

    if len(metadata) > MAX_METADATA_LENGTH:
        raise INVALID_METADATA

    try:
        # this also raises an error if there's some data remaining
        decoded = cbor.decode(metadata)
    except Exception:
        raise INVALID_METADATA

    if not isinstance(decoded, dict):
        raise INVALID_METADATA


def _serialize_tx(keychain: seed.Keychain, msg: CardanoSignTx) -> Tuple[bytes, bytes]:
    tx_body = _build_tx_body(keychain, msg)
    tx_hash = _hash_tx_body(tx_body)

    witnesses = _build_witnesses(
        keychain,
        msg.inputs,
        msg.certificates,
        msg.withdrawals,
        tx_hash,
        msg.protocol_magic,
    )

    metadata = None
    if msg.metadata:
        metadata = cbor.Raw(bytes(msg.metadata))

    serialized_tx = cbor.encode([tx_body, witnesses, metadata])

    return serialized_tx, tx_hash


def _build_tx_body(keychain: seed.Keychain, msg: CardanoSignTx) -> Dict:
    inputs_for_cbor = _build_inputs(msg.inputs)
    outputs_for_cbor = _build_outputs(
        keychain, msg.outputs, msg.protocol_magic, msg.network_id
    )

    tx_body = {
        0: inputs_for_cbor,
        1: outputs_for_cbor,
        2: msg.fee,
        3: msg.ttl,
    }

    if msg.certificates:
        certificates_for_cbor = _build_certificates(keychain, msg.certificates)
        tx_body[4] = certificates_for_cbor

    if msg.withdrawals:
        withdrawals_for_cbor = _build_withdrawals(
            keychain, msg.withdrawals, msg.protocol_magic, msg.network_id
        )
        tx_body[5] = withdrawals_for_cbor

    # tx_body[6] is for protocol updates, which we don't support

    if msg.metadata:
        tx_body[7] = _hash_metadata(bytes(msg.metadata))

    return tx_body


def _build_inputs(inputs: List[CardanoTxInputType]) -> List[Tuple[bytes, int]]:
    return [(input.prev_hash, input.prev_index) for input in inputs]


def _build_outputs(
    keychain: seed.Keychain,
    outputs: List[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> List[Tuple[bytes, int]]:
    result = []
    for output in outputs:
        amount = output.amount
        if output.address_parameters:
            address = derive_address_bytes(
                keychain, output.address_parameters, protocol_magic, network_id
            )
        else:
            # output address is validated in _validate_outputs before this happens
            address = get_address_bytes_unsafe(output.address)

        result.append((address, amount))

    return result


def _build_certificates(
    keychain: seed.Keychain, certificates: List[CardanoTxCertificateType]
) -> List[Tuple]:
    result = []
    for certificate in certificates:
        public_key_hash = get_public_key_hash(keychain, certificate.path)

        stake_credential = [0, public_key_hash]
        if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
            certificate_for_cbor = (
                certificate.type,
                stake_credential,
                certificate.pool,
            )
        else:
            certificate_for_cbor = (certificate.type, stake_credential)

        result.append(certificate_for_cbor)

    return result


def _build_withdrawals(
    keychain: seed.Keychain,
    withdrawals: List[CardanoTxWithdrawalType],
    protocol_magic: int,
    network_id: int,
) -> Dict[bytes, int]:
    result = {}
    for withdrawal in withdrawals:
        reward_address = derive_address_bytes(
            keychain,
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD, address_n=withdrawal.path,
            ),
            protocol_magic,
            network_id,
        )

        result[reward_address] = withdrawal.amount

    return result


def _hash_metadata(metadata: bytes) -> bytes:
    return hashlib.blake2b(data=metadata, outlen=METADATA_HASH_SIZE).digest()


def _hash_tx_body(tx_body: Dict) -> bytes:
    tx_body_cbor = cbor.encode(tx_body)
    return hashlib.blake2b(data=tx_body_cbor, outlen=32).digest()


def _build_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    certificates: List[CardanoTxCertificateType],
    withdrawals: List[CardanoTxWithdrawalType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> Dict:
    shelley_witnesses = _build_shelley_witnesses(
        keychain, inputs, certificates, withdrawals, tx_body_hash
    )
    byron_witnesses = _build_byron_witnesses(
        keychain, inputs, tx_body_hash, protocol_magic
    )

    # use key 0 for shelley witnesses and key 2 for byron witnesses
    # according to the spec in shelley.cddl in cardano-ledger-specs
    witnesses = {}
    if shelley_witnesses:
        witnesses[0] = shelley_witnesses
    if byron_witnesses:
        witnesses[2] = byron_witnesses

    return witnesses


def _build_shelley_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    certificates: List[CardanoTxCertificateType],
    withdrawals: List[CardanoTxWithdrawalType],
    tx_body_hash: bytes,
) -> List[Tuple[bytes, bytes]]:
    shelley_witnesses = []

    # include only one witness for each path
    paths = set()
    for input in inputs:
        if not is_shelley_path(input.address_n):
            continue
        paths.add(tuple(input.address_n))
    for certificate in certificates:
        if not _is_certificate_witness_required(certificate.type):
            continue
        paths.add(tuple(certificate.path))
    for withdrawal in withdrawals:
        paths.add(tuple(withdrawal.path))

    for path in paths:
        witness = _build_shelley_witness(keychain, tx_body_hash, list(path))
        shelley_witnesses.append(witness)

    return shelley_witnesses


def _build_shelley_witness(
    keychain: seed.Keychain, tx_body_hash: bytes, path: List[int]
) -> List[Tuple[bytes, bytes]]:
    node = keychain.derive(path)

    signature = ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), tx_body_hash
    )
    public_key = remove_ed25519_prefix(node.public_key())

    return public_key, signature


def _is_certificate_witness_required(certificate_type: int) -> bool:
    return certificate_type != CardanoCertificateType.STAKE_REGISTRATION


def _build_byron_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> List[Tuple[bytes, bytes, bytes, bytes]]:
    byron_witnesses = []

    # include only one witness for each path
    paths = set()
    for input in inputs:
        if not is_byron_path(input.address_n):
            continue
        paths.add(tuple(input.address_n))

    for path in paths:
        node = keychain.derive(list(path))

        public_key = remove_ed25519_prefix(node.public_key())
        signature = ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )
        chain_code = node.chain_code()
        address_attributes = cbor.encode(get_address_attributes(protocol_magic))

        byron_witnesses.append((public_key, signature, chain_code, address_attributes))

    return byron_witnesses


async def _show_tx(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> None:
    total_amount = await _show_outputs(ctx, keychain, msg)

    for certificate in msg.certificates:
        await confirm_certificate(ctx, certificate)

    for withdrawal in msg.withdrawals:
        await confirm_withdrawal(ctx, withdrawal)

    has_metadata = bool(msg.metadata)
    await confirm_transaction(
        ctx, total_amount, msg.fee, msg.protocol_magic, has_metadata
    )


async def _show_outputs(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> int:
    total_amount = 0
    for output in msg.outputs:
        if output.address_parameters:
            address = derive_human_readable_address(
                keychain, output.address_parameters, msg.protocol_magic, msg.network_id
            )

            await _show_change_output_staking_warnings(
                ctx, keychain, output.address_parameters, address, output.amount
            )

            if _should_hide_output(output.address_parameters.address_n, msg.inputs):
                continue
        else:
            address = output.address

        total_amount += output.amount

        await confirm_sending(ctx, output.amount, address)

    return total_amount


async def _show_change_output_staking_warnings(
    ctx: wire.Context,
    keychain: seed.Keychain,
    address_parameters: CardanoAddressParametersType,
    address: str,
    amount: int,
):
    address_type = address_parameters.address_type

    staking_use_case = staking_use_cases.get(keychain, address_parameters)
    if staking_use_case == staking_use_cases.NO_STAKING:
        await show_warning_tx_no_staking_info(ctx, address_type, amount)
    elif staking_use_case == staking_use_cases.POINTER_ADDRESS:
        await show_warning_tx_pointer_address(
            ctx, address_parameters.certificate_pointer, amount,
        )
    elif staking_use_case == staking_use_cases.MISMATCH:
        if address_parameters.address_n_staking:
            await show_warning_tx_different_staking_account(
                ctx, to_account_path(address_parameters.address_n_staking), amount,
            )
        else:
            await show_warning_tx_staking_key_hash(
                ctx, address_parameters.staking_key_hash, amount,
            )


# addresses from the same account as inputs should be hidden
def _should_hide_output(output: List[int], inputs: List[CardanoTxInputType]) -> bool:
    for input in inputs:
        inp = input.address_n
        if (
            len(output) != BIP_PATH_LENGTH
            or output[: (ACCOUNT_PATH_INDEX + 1)] != inp[: (ACCOUNT_PATH_INDEX + 1)]
            or output[-2] >= 2
            or output[-1] >= MAX_CHANGE_ADDRESS_INDEX
        ):
            return False
    return True
