from trezor import log, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import (
    CardanoAddressParametersType,
    CardanoAddressType,
    CardanoCertificateType,
    CardanoSignedTx,
    CardanoSignedTxChunk,
    CardanoSignedTxChunkAck,
)

from apps.common import cbor, safety_checks
from apps.common.paths import validate_path
from apps.common.seed import remove_ed25519_prefix

from . import seed
from .address import (
    derive_address_bytes,
    derive_human_readable_address,
    get_address_bytes_unsafe,
    validate_output_address,
)
from .byron_address import get_address_attributes
from .certificates import cborize_certificate, validate_certificate
from .helpers import (
    INVALID_METADATA,
    INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE,
    INVALID_STAKEPOOL_REGISTRATION_TX_INPUTS,
    INVALID_TOKEN_BUNDLE_OUTPUT,
    INVALID_WITHDRAWAL,
    LOVELACE_MAX_SUPPLY,
    network_ids,
    protocol_magics,
    staking_use_cases,
)
from .helpers.paths import (
    ACCOUNT_PATH_INDEX,
    BIP_PATH_LENGTH,
    CERTIFICATE_PATH_NAME,
    CHANGE_OUTPUT_PATH_NAME,
    CHANGE_OUTPUT_STAKING_PATH_NAME,
    MAX_SAFE_ACCOUNT_INDEX,
    MAX_SAFE_CHANGE_ADDRESS_INDEX,
    POOL_OWNER_STAKING_PATH_NAME,
    SCHEMA_ADDRESS,
    SCHEMA_STAKING,
    SCHEMA_STAKING_ANY_ACCOUNT,
)
from .helpers.utils import to_account_path
from .layout import (
    confirm_certificate,
    confirm_sending,
    confirm_stake_pool_metadata,
    confirm_stake_pool_owners,
    confirm_stake_pool_parameters,
    confirm_stake_pool_registration_final,
    confirm_transaction,
    confirm_transaction_network_ttl,
    confirm_withdrawal,
    show_warning_path,
    show_warning_tx_different_staking_account,
    show_warning_tx_network_unverifiable,
    show_warning_tx_no_staking_info,
    show_warning_tx_output_contains_tokens,
    show_warning_tx_pointer_address,
    show_warning_tx_staking_key_hash,
)
from .seed import is_byron_path, is_shelley_path

if False:
    from typing import Any, Optional, Union

    from trezor.messages import CardanoSignTx
    from trezor.messages import CardanoTxCertificateType
    from trezor.messages import CardanoTxInputType
    from trezor.messages import CardanoTxOutputType
    from trezor.messages import CardanoTxWithdrawalType
    from trezor.messages import CardanoAssetGroupType

    from apps.common.cbor import CborSequence
    from apps.common.paths import PathSchema

    CborizedTokenBundle = dict[bytes, dict[bytes, int]]
    CborizedTxOutput = tuple[bytes, Union[int, tuple[int, CborizedTokenBundle]]]
    CborizedSignedTx = tuple[dict, dict, Optional[cbor.Raw]]
    TxHash = bytes

METADATA_HASH_SIZE = 32
MINTING_POLICY_ID_LENGTH = 28
MAX_METADATA_LENGTH = 500
MAX_ASSET_NAME_LENGTH = 32
MAX_TX_CHUNK_SIZE = 256


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTx, keychain: seed.Keychain
) -> CardanoSignedTx:
    if msg.fee > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Fee is out of range!")

    validate_network_info(msg.network_id, msg.protocol_magic)

    try:
        if _has_stake_pool_registration(msg):
            cborized_tx, tx_hash = await _sign_stake_pool_registration_tx(
                ctx, msg, keychain
            )
        else:
            cborized_tx, tx_hash = await _sign_ordinary_tx(ctx, msg, keychain)

        signed_tx_chunks = cbor.encode_chunked(cborized_tx, MAX_TX_CHUNK_SIZE)

        for signed_tx_chunk in signed_tx_chunks:
            response = CardanoSignedTxChunk(signed_tx_chunk=signed_tx_chunk)
            await ctx.call(response, CardanoSignedTxChunkAck)

        return CardanoSignedTx(tx_hash=tx_hash, serialized_tx=None)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")


async def _sign_ordinary_tx(
    ctx: wire.Context, msg: CardanoSignTx, keychain: seed.Keychain
) -> tuple[CborizedSignedTx, TxHash]:
    for i in msg.inputs:
        await validate_path(
            ctx, keychain, i.address_n, SCHEMA_ADDRESS.match(i.address_n)
        )

    _validate_outputs(keychain, msg.outputs, msg.protocol_magic, msg.network_id)
    _validate_certificates(msg.certificates, msg.protocol_magic, msg.network_id)
    _validate_withdrawals(msg.withdrawals)
    _validate_metadata(msg.metadata)

    # display the transaction in UI
    await _show_standard_tx(ctx, keychain, msg)

    return _cborize_signed_tx(keychain, msg)


async def _sign_stake_pool_registration_tx(
    ctx: wire.Context, msg: CardanoSignTx, keychain: seed.Keychain
) -> tuple[CborizedSignedTx, TxHash]:
    """
    We have a separate tx signing flow for stake pool registration because it's a
    transaction where the witnessable entries (i.e. inputs, withdrawals, etc.)
    in the transaction are not supposed to be controlled by the HW wallet, which
    means the user is vulnerable to unknowingly supplying a witness for an UTXO
    or other tx entry they think is external, resulting in the co-signers
    gaining control over their funds (Something SLIP-0019 is dealing with for
    BTC but no similar standard is currently available for Cardano). Hence we
    completely forbid witnessing inputs and other entries of the transaction
    except the stake pool certificate itself and we provide a witness only to the
    user's staking key in the list of pool owners.
    """
    _validate_stake_pool_registration_tx_structure(msg)

    _ensure_no_signing_inputs(msg.inputs)
    _validate_outputs(keychain, msg.outputs, msg.protocol_magic, msg.network_id)
    _validate_certificates(msg.certificates, msg.protocol_magic, msg.network_id)
    _validate_metadata(msg.metadata)

    await _show_stake_pool_registration_tx(ctx, keychain, msg)

    return _cborize_signed_tx(keychain, msg)


def _has_stake_pool_registration(msg: CardanoSignTx) -> bool:
    return any(
        cert.type == CardanoCertificateType.STAKE_POOL_REGISTRATION
        for cert in msg.certificates
    )


def validate_network_info(network_id: int, protocol_magic: int) -> None:
    """
    We are only concerned about checking that both network_id and protocol_magic
    belong to the mainnet or that both belong to a testnet. We don't need to check for
    consistency between various testnets (at least for now).
    """
    is_mainnet_network_id = network_ids.is_mainnet(network_id)
    is_mainnet_protocol_magic = protocol_magics.is_mainnet(protocol_magic)

    if is_mainnet_network_id != is_mainnet_protocol_magic:
        raise wire.ProcessError("Invalid network id/protocol magic combination!")


def _validate_stake_pool_registration_tx_structure(msg: CardanoSignTx) -> None:
    # ensures that there is exactly one certificate, which is stake pool registration,
    # and no withdrawals
    if (
        len(msg.certificates) != 1
        or not _has_stake_pool_registration(msg)
        or len(msg.withdrawals) != 0
    ):
        raise INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE


def _validate_outputs(
    keychain: seed.Keychain,
    outputs: list[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> None:
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

        _validate_token_bundle(output.token_bundle)

    if total_amount > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Total transaction amount is out of range!")


def _validate_token_bundle(token_bundle: list[CardanoAssetGroupType]) -> None:
    seen_policy_ids = set()
    for token_group in token_bundle:
        policy_id = bytes(token_group.policy_id)

        if len(policy_id) != MINTING_POLICY_ID_LENGTH:
            raise INVALID_TOKEN_BUNDLE_OUTPUT

        if policy_id in seen_policy_ids:
            raise INVALID_TOKEN_BUNDLE_OUTPUT
        else:
            seen_policy_ids.add(policy_id)

        if not token_group.tokens:
            raise INVALID_TOKEN_BUNDLE_OUTPUT

        seen_asset_name_bytes = set()
        for token in token_group.tokens:
            asset_name_bytes = bytes(token.asset_name_bytes)
            if len(asset_name_bytes) > MAX_ASSET_NAME_LENGTH:
                raise INVALID_TOKEN_BUNDLE_OUTPUT

            if asset_name_bytes in seen_asset_name_bytes:
                raise INVALID_TOKEN_BUNDLE_OUTPUT
            else:
                seen_asset_name_bytes.add(asset_name_bytes)


def _ensure_no_signing_inputs(inputs: list[CardanoTxInputType]) -> None:
    if any(i.address_n for i in inputs):
        raise INVALID_STAKEPOOL_REGISTRATION_TX_INPUTS


def _validate_certificates(
    certificates: list[CardanoTxCertificateType], protocol_magic: int, network_id: int
) -> None:
    for certificate in certificates:
        validate_certificate(certificate, protocol_magic, network_id)


def _validate_withdrawals(withdrawals: list[CardanoTxWithdrawalType]) -> None:
    for withdrawal in withdrawals:
        if not SCHEMA_STAKING_ANY_ACCOUNT.match(withdrawal.path):
            raise INVALID_WITHDRAWAL

        if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
            raise INVALID_WITHDRAWAL


def _validate_metadata(metadata: bytes | None) -> None:
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


def _cborize_signed_tx(
    keychain: seed.Keychain, msg: CardanoSignTx
) -> tuple[CborizedSignedTx, TxHash]:
    tx_body = _cborize_tx_body(keychain, msg)
    tx_hash = _hash_tx_body(tx_body)

    witnesses = _cborize_witnesses(
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

    return (tx_body, witnesses, metadata), tx_hash


def _cborize_tx_body(keychain: seed.Keychain, msg: CardanoSignTx) -> dict:
    inputs_for_cbor = _cborize_inputs(msg.inputs)
    outputs_for_cbor = _cborize_outputs(
        keychain, msg.outputs, msg.protocol_magic, msg.network_id
    )

    tx_body = {
        0: inputs_for_cbor,
        1: outputs_for_cbor,
        2: msg.fee,
    }

    if msg.ttl:
        tx_body[3] = msg.ttl

    if msg.certificates:
        certificates_for_cbor = _cborize_certificates(keychain, msg.certificates)
        tx_body[4] = certificates_for_cbor

    if msg.withdrawals:
        withdrawals_for_cbor = _cborize_withdrawals(
            keychain, msg.withdrawals, msg.protocol_magic, msg.network_id
        )
        tx_body[5] = withdrawals_for_cbor

    # tx_body[6] is for protocol updates, which we don't support

    if msg.metadata:
        tx_body[7] = _hash_metadata(bytes(msg.metadata))

    if msg.validity_interval_start:
        tx_body[8] = msg.validity_interval_start

    return tx_body


def _cborize_inputs(inputs: list[CardanoTxInputType]) -> list[tuple[bytes, int]]:
    return [(tx_input.prev_hash, tx_input.prev_index) for tx_input in inputs]


def _cborize_outputs(
    keychain: seed.Keychain,
    outputs: list[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> list[CborizedTxOutput]:
    return [
        _cborize_output(keychain, output, protocol_magic, network_id)
        for output in outputs
    ]


def _cborize_output(
    keychain: seed.Keychain,
    output: CardanoTxOutputType,
    protocol_magic: int,
    network_id: int,
) -> CborizedTxOutput:
    amount = output.amount
    if output.address_parameters:
        address = derive_address_bytes(
            keychain, output.address_parameters, protocol_magic, network_id
        )
    else:
        assert output.address is not None  # _validate_outputs
        address = get_address_bytes_unsafe(output.address)

    if not output.token_bundle:
        return (address, amount)
    else:
        return (address, (amount, _cborize_token_bundle(output.token_bundle)))


def _cborize_token_bundle(
    token_bundle: list[CardanoAssetGroupType],
) -> CborizedTokenBundle:
    result: CborizedTokenBundle = {}

    for token_group in token_bundle:
        cborized_policy_id = bytes(token_group.policy_id)
        cborized_token_group = result[cborized_policy_id] = {}

        for token in token_group.tokens:
            cborized_asset_name = bytes(token.asset_name_bytes)
            cborized_token_group[cborized_asset_name] = token.amount

    return result


def _cborize_certificates(
    keychain: seed.Keychain,
    certificates: list[CardanoTxCertificateType],
) -> list[CborSequence]:
    return [cborize_certificate(keychain, cert) for cert in certificates]


def _cborize_withdrawals(
    keychain: seed.Keychain,
    withdrawals: list[CardanoTxWithdrawalType],
    protocol_magic: int,
    network_id: int,
) -> dict[bytes, int]:
    result = {}
    for withdrawal in withdrawals:
        reward_address = derive_address_bytes(
            keychain,
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD,
                address_n=withdrawal.path,
            ),
            protocol_magic,
            network_id,
        )

        result[reward_address] = withdrawal.amount

    return result


def _hash_metadata(metadata: bytes) -> bytes:
    return hashlib.blake2b(data=metadata, outlen=METADATA_HASH_SIZE).digest()


def _hash_tx_body(tx_body: dict) -> bytes:
    tx_body_cbor_chunks = cbor.encode_streamed(tx_body)

    hashfn = hashlib.blake2b(outlen=32)
    for chunk in tx_body_cbor_chunks:
        hashfn.update(chunk)

    return hashfn.digest()


def _cborize_witnesses(
    keychain: seed.Keychain,
    inputs: list[CardanoTxInputType],
    certificates: list[CardanoTxCertificateType],
    withdrawals: list[CardanoTxWithdrawalType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> dict:
    shelley_witnesses = _cborize_shelley_witnesses(
        keychain, inputs, certificates, withdrawals, tx_body_hash
    )
    byron_witnesses = _cborize_byron_witnesses(
        keychain, inputs, tx_body_hash, protocol_magic
    )

    # use key 0 for shelley witnesses and key 2 for byron witnesses
    # according to the spec in shelley.cddl in cardano-ledger-specs
    witnesses: dict[Any, Any] = {}
    if shelley_witnesses:
        witnesses[0] = shelley_witnesses
    if byron_witnesses:
        witnesses[2] = byron_witnesses

    return witnesses


def _cborize_shelley_witnesses(
    keychain: seed.Keychain,
    inputs: list[CardanoTxInputType],
    certificates: list[CardanoTxCertificateType],
    withdrawals: list[CardanoTxWithdrawalType],
    tx_body_hash: bytes,
) -> list[tuple[bytes, bytes]]:
    shelley_witnesses = []

    # include only one witness for each path
    paths = set()
    for tx_input in inputs:
        if is_shelley_path(tx_input.address_n):
            paths.add(tuple(tx_input.address_n))
    for certificate in certificates:
        if certificate.type in (
            CardanoCertificateType.STAKE_DEREGISTRATION,
            CardanoCertificateType.STAKE_DELEGATION,
        ):
            paths.add(tuple(certificate.path))
        elif certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            # ensured by validate_certificate:
            assert certificate.pool_parameters is not None  # validate_certificate
            for pool_owner in certificate.pool_parameters.owners:
                if pool_owner.staking_key_path:
                    paths.add(tuple(pool_owner.staking_key_path))
    for withdrawal in withdrawals:
        paths.add(tuple(withdrawal.path))

    for path in paths:
        witness = _cborize_shelley_witness(keychain, tx_body_hash, list(path))
        shelley_witnesses.append(witness)

    shelley_witnesses.sort()

    return shelley_witnesses


def _cborize_shelley_witness(
    keychain: seed.Keychain, tx_body_hash: bytes, path: list[int]
) -> tuple[bytes, bytes]:
    node = keychain.derive(path)

    signature = ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), tx_body_hash
    )
    public_key = remove_ed25519_prefix(node.public_key())

    return public_key, signature


def _cborize_byron_witnesses(
    keychain: seed.Keychain,
    inputs: list[CardanoTxInputType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> list[tuple[bytes, bytes, bytes, bytes]]:
    byron_witnesses = []

    # include only one witness for each path
    paths = set()
    for tx_input in inputs:
        if is_byron_path(tx_input.address_n):
            paths.add(tuple(tx_input.address_n))

    for path in paths:
        node = keychain.derive(list(path))

        public_key = remove_ed25519_prefix(node.public_key())
        signature = ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )
        chain_code = node.chain_code()
        address_attributes = cbor.encode(get_address_attributes(protocol_magic))

        byron_witnesses.append((public_key, signature, chain_code, address_attributes))

    byron_witnesses.sort()

    return byron_witnesses


async def _show_standard_tx(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> None:
    is_network_id_verifiable = _is_network_id_verifiable(msg)

    if not is_network_id_verifiable:
        await show_warning_tx_network_unverifiable(ctx)

    total_amount = await _show_outputs(ctx, keychain, msg)

    for certificate in msg.certificates:
        await _fail_or_warn_if_invalid_path(
            ctx, SCHEMA_STAKING, certificate.path, CERTIFICATE_PATH_NAME
        )
        await confirm_certificate(ctx, certificate)

    for withdrawal in msg.withdrawals:
        await confirm_withdrawal(ctx, withdrawal)

    has_metadata = bool(msg.metadata)
    await confirm_transaction(
        ctx=ctx,
        amount=total_amount,
        fee=msg.fee,
        protocol_magic=msg.protocol_magic,
        ttl=msg.ttl,
        validity_interval_start=msg.validity_interval_start,
        has_metadata=has_metadata,
        is_network_id_verifiable=is_network_id_verifiable,
    )


async def _show_stake_pool_registration_tx(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> None:
    stake_pool_registration_certificate = msg.certificates[0]
    pool_parameters = stake_pool_registration_certificate.pool_parameters
    # _validate_stake_pool_registration_tx_structure ensures that there is only one
    # certificate, and validate_certificate ensures that the structure is valid
    assert pool_parameters is not None

    # display the transaction (certificate) in UI
    await confirm_stake_pool_parameters(
        ctx, pool_parameters, msg.network_id, msg.protocol_magic
    )

    for owner in pool_parameters.owners:
        if owner.staking_key_path:
            await _fail_or_warn_if_invalid_path(
                ctx,
                SCHEMA_STAKING,
                owner.staking_key_path,
                POOL_OWNER_STAKING_PATH_NAME,
            )

    await confirm_stake_pool_owners(
        ctx, keychain, pool_parameters.owners, msg.network_id
    )
    await confirm_stake_pool_metadata(ctx, pool_parameters.metadata)
    await confirm_transaction_network_ttl(
        ctx, msg.protocol_magic, msg.ttl, msg.validity_interval_start
    )
    await confirm_stake_pool_registration_final(ctx)


async def _show_outputs(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> int:
    total_amount = 0
    for output in msg.outputs:
        if output.address_parameters:
            await _fail_or_warn_if_invalid_path(
                ctx,
                SCHEMA_ADDRESS,
                output.address_parameters.address_n,
                CHANGE_OUTPUT_PATH_NAME,
            )

            await _show_change_output_staking_warnings(
                ctx, keychain, output.address_parameters, output.amount
            )

            if _should_hide_output(output.address_parameters.address_n, msg.inputs):
                continue

            address = derive_human_readable_address(
                keychain, output.address_parameters, msg.protocol_magic, msg.network_id
            )
        else:
            assert output.address is not None  # _validate_outputs
            address = output.address

        total_amount += output.amount

        if len(output.token_bundle) > 0:
            await show_warning_tx_output_contains_tokens(ctx)

        await confirm_sending(ctx, output.amount, output.token_bundle, address)

    return total_amount


async def _show_change_output_staking_warnings(
    ctx: wire.Context,
    keychain: seed.Keychain,
    address_parameters: CardanoAddressParametersType,
    amount: int,
) -> None:
    address_type = address_parameters.address_type

    if (
        address_type == CardanoAddressType.BASE
        and not address_parameters.staking_key_hash
    ):
        await _fail_or_warn_if_invalid_path(
            ctx,
            SCHEMA_STAKING,
            address_parameters.address_n_staking,
            CHANGE_OUTPUT_STAKING_PATH_NAME,
        )

    staking_use_case = staking_use_cases.get(keychain, address_parameters)
    if staking_use_case == staking_use_cases.NO_STAKING:
        await show_warning_tx_no_staking_info(ctx, address_type, amount)
    elif staking_use_case == staking_use_cases.POINTER_ADDRESS:
        # ensured in _derive_shelley_address:
        assert address_parameters.certificate_pointer is not None
        await show_warning_tx_pointer_address(
            ctx,
            address_parameters.certificate_pointer,
            amount,
        )
    elif staking_use_case == staking_use_cases.MISMATCH:
        if address_parameters.address_n_staking:
            await show_warning_tx_different_staking_account(
                ctx,
                to_account_path(address_parameters.address_n_staking),
                amount,
            )
        else:
            # ensured in _validate_base_address_staking_info:
            assert address_parameters.staking_key_hash
            await show_warning_tx_staking_key_hash(
                ctx,
                address_parameters.staking_key_hash,
                amount,
            )


# addresses from the same account as inputs should be hidden
def _should_hide_output(output: list[int], inputs: list[CardanoTxInputType]) -> bool:
    for tx_input in inputs:
        inp = tx_input.address_n
        if (
            len(output) != BIP_PATH_LENGTH
            or output[ACCOUNT_PATH_INDEX] != inp[ACCOUNT_PATH_INDEX]
            or output[ACCOUNT_PATH_INDEX] > MAX_SAFE_ACCOUNT_INDEX
            or output[-2] >= 2
            or output[-1] >= MAX_SAFE_CHANGE_ADDRESS_INDEX
        ):
            return False
    return True


def _is_network_id_verifiable(msg: CardanoSignTx) -> bool:
    """
    checks whether there is at least one element that contains
    information about network ID, otherwise Trezor cannot
    guarantee that the tx is actually meant for the given network
    """
    return (
        len(msg.outputs) != 0
        or len(msg.withdrawals) != 0
        or _has_stake_pool_registration(msg)
    )


async def _fail_or_warn_if_invalid_path(
    ctx: wire.Context, schema: PathSchema, path: list[int], path_name: str
) -> None:
    if not schema.match(path):
        if safety_checks.is_strict():
            raise wire.DataError("Invalid %s" % path_name.lower())
        else:
            await show_warning_path(ctx, path, path_name)
