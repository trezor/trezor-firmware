from micropython import const

from trezor import log, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.enums import (
    CardanoAddressType,
    CardanoCertificateType,
    CardanoTxSigningMode,
    CardanoTxWitnessType,
)
from trezor.messages import (
    CardanoAddressParametersType,
    CardanoAssetGroup,
    CardanoPoolOwner,
    CardanoPoolRelayParameters,
    CardanoSignTxFinished,
    CardanoSignTxInit,
    CardanoToken,
    CardanoTxAuxiliaryData,
    CardanoTxBodyHash,
    CardanoTxCertificate,
    CardanoTxHostAck,
    CardanoTxInput,
    CardanoTxItemAck,
    CardanoTxOutput,
    CardanoTxWithdrawal,
    CardanoTxWitnessRequest,
    CardanoTxWitnessResponse,
)

from apps.common import cbor, safety_checks

from . import seed
from .address import (
    derive_address_bytes,
    derive_human_readable_address,
    get_address_bytes_unsafe,
    validate_address_parameters,
    validate_output_address,
)
from .auxiliary_data import (
    get_auxiliary_data_hash_and_supplement,
    show_auxiliary_data,
    validate_auxiliary_data,
)
from .certificates import (
    assert_certificate_cond,
    cborize_certificate,
    cborize_initial_pool_registration_certificate_fields,
    cborize_pool_metadata,
    cborize_pool_owner,
    cborize_pool_relay,
    validate_certificate,
    validate_pool_owner,
    validate_pool_relay,
)
from .helpers import (
    INVALID_OUTPUT,
    INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE,
    INVALID_STAKEPOOL_REGISTRATION_TX_WITNESSES,
    INVALID_TOKEN_BUNDLE_OUTPUT,
    INVALID_WITHDRAWAL,
    LOVELACE_MAX_SUPPLY,
    network_ids,
    protocol_magics,
    staking_use_cases,
)
from .helpers.account_path_check import AccountPathChecker
from .helpers.hash_builder_collection import HashBuilderDict, HashBuilderList
from .helpers.paths import (
    CERTIFICATE_PATH_NAME,
    CHANGE_OUTPUT_PATH_NAME,
    CHANGE_OUTPUT_STAKING_PATH_NAME,
    POOL_OWNER_STAKING_PATH_NAME,
    SCHEMA_PAYMENT,
    SCHEMA_STAKING,
    SCHEMA_STAKING_ANY_ACCOUNT,
    WITNESS_PATH_NAME,
)
from .helpers.utils import derive_public_key, to_account_path
from .layout import (
    confirm_certificate,
    confirm_sending,
    confirm_sending_token,
    confirm_stake_pool_metadata,
    confirm_stake_pool_owner,
    confirm_stake_pool_parameters,
    confirm_stake_pool_registration_final,
    confirm_transaction,
    confirm_withdrawal,
    show_warning_path,
    show_warning_tx_different_staking_account,
    show_warning_tx_network_unverifiable,
    show_warning_tx_no_staking_info,
    show_warning_tx_output_contains_tokens,
    show_warning_tx_pointer_address,
    show_warning_tx_staking_key_hash,
)
from .seed import is_byron_path

if False:
    from typing import Any, Union
    from apps.common.paths import PathSchema

    CardanoTxResponseType = Union[CardanoTxItemAck, CardanoTxWitnessResponse]

MINTING_POLICY_ID_LENGTH = 28
MAX_ASSET_NAME_LENGTH = 32

TX_BODY_KEY_INPUTS = const(0)
TX_BODY_KEY_OUTPUTS = const(1)
TX_BODY_KEY_FEE = const(2)
TX_BODY_KEY_TTL = const(3)
TX_BODY_KEY_CERTIFICATES = const(4)
TX_BODY_KEY_WITHDRAWALS = const(5)
TX_BODY_KEY_AUXILIARY_DATA = const(7)
TX_BODY_KEY_VALIDITY_INTERVAL_START = const(8)

POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT = 10


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTxInit, keychain: seed.Keychain
) -> CardanoSignTxFinished:
    is_network_id_verifiable = await _validate_tx_signing_request(ctx, msg)

    # inputs, outputs and fee are mandatory fields, count the number of optional fields present
    tx_body_map_item_count = 3 + sum(
        (
            msg.ttl is not None,
            msg.certificates_count > 0,
            msg.withdrawals_count > 0,
            msg.has_auxiliary_data,
            msg.validity_interval_start is not None,
        )
    )

    account_path_checker = AccountPathChecker()

    hash_fn = hashlib.blake2b(outlen=32)
    tx_dict: HashBuilderDict[int, Any] = HashBuilderDict(tx_body_map_item_count)
    tx_dict.start(hash_fn)
    with tx_dict:
        await _process_transaction(ctx, msg, keychain, tx_dict, account_path_checker)

    await _confirm_transaction(ctx, msg, is_network_id_verifiable)

    try:
        tx_hash = hash_fn.digest()
        response_after_witness_requests = await _process_witness_requests(
            ctx,
            keychain,
            tx_hash,
            msg.witness_requests_count,
            msg.signing_mode,
            account_path_checker,
        )
        await ctx.call(response_after_witness_requests, CardanoTxHostAck)

        await ctx.call(CardanoTxBodyHash(tx_hash=tx_hash), CardanoTxHostAck)
        return CardanoSignTxFinished()

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")


async def _validate_tx_signing_request(
    ctx: wire.Context, msg: CardanoSignTxInit
) -> bool:
    """Validate the data in the signing request and return whether the provided network id is verifiable."""
    if msg.fee > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Fee is out of range!")
    validate_network_info(msg.network_id, msg.protocol_magic)

    is_network_id_verifiable = _is_network_id_verifiable(msg)
    if msg.signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        if not is_network_id_verifiable:
            await show_warning_tx_network_unverifiable(ctx)
    elif msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        _validate_stake_pool_registration_tx_structure(msg)

    return is_network_id_verifiable


async def _process_transaction(
    ctx: wire.Context,
    msg: CardanoSignTxInit,
    keychain: seed.Keychain,
    tx_dict: HashBuilderDict,
    account_path_checker: AccountPathChecker,
) -> None:
    inputs_list: HashBuilderList[tuple[bytes, int]] = HashBuilderList(msg.inputs_count)
    with tx_dict.add(TX_BODY_KEY_INPUTS, inputs_list):
        await _process_inputs(ctx, inputs_list, msg.inputs_count)

    outputs_list: HashBuilderList = HashBuilderList(msg.outputs_count)
    with tx_dict.add(TX_BODY_KEY_OUTPUTS, outputs_list):
        await _process_outputs(
            ctx,
            keychain,
            outputs_list,
            msg.outputs_count,
            msg.signing_mode,
            msg.protocol_magic,
            msg.network_id,
            account_path_checker,
        )

    tx_dict.add(TX_BODY_KEY_FEE, msg.fee)

    if msg.ttl is not None:
        tx_dict.add(TX_BODY_KEY_TTL, msg.ttl)

    if msg.certificates_count > 0:
        certificates_list: HashBuilderList = HashBuilderList(msg.certificates_count)
        with tx_dict.add(TX_BODY_KEY_CERTIFICATES, certificates_list):
            await _process_certificates(
                ctx,
                keychain,
                certificates_list,
                msg.certificates_count,
                msg.signing_mode,
                msg.protocol_magic,
                msg.network_id,
                account_path_checker,
            )

    if msg.withdrawals_count > 0:
        withdrawals_dict: HashBuilderDict[bytes, int] = HashBuilderDict(
            msg.withdrawals_count
        )
        with tx_dict.add(TX_BODY_KEY_WITHDRAWALS, withdrawals_dict):
            await _process_withdrawals(
                ctx,
                keychain,
                withdrawals_dict,
                msg.withdrawals_count,
                msg.protocol_magic,
                msg.network_id,
                account_path_checker,
            )

    if msg.has_auxiliary_data:
        await _process_auxiliary_data(
            ctx,
            keychain,
            tx_dict,
            msg.protocol_magic,
            msg.network_id,
        )

    if msg.validity_interval_start is not None:
        tx_dict.add(TX_BODY_KEY_VALIDITY_INTERVAL_START, msg.validity_interval_start)


async def _confirm_transaction(
    ctx: wire.Context,
    msg: CardanoSignTxInit,
    is_network_id_verifiable: bool,
) -> None:
    if msg.signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        await confirm_transaction(
            ctx,
            msg.fee,
            msg.protocol_magic,
            msg.ttl,
            msg.validity_interval_start,
            is_network_id_verifiable,
        )
    elif msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await confirm_stake_pool_registration_final(
            ctx, msg.protocol_magic, msg.ttl, msg.validity_interval_start
        )


async def _process_inputs(
    ctx: wire.Context,
    inputs_list: HashBuilderList[tuple[bytes, int]],
    inputs_count: int,
) -> None:
    """Read, validate and serialize the inputs."""
    for index in range(inputs_count):
        input: CardanoTxInput = await ctx.call(CardanoTxItemAck(), CardanoTxInput)
        inputs_list.append((input.prev_hash, input.prev_index))


async def _process_outputs(
    ctx: wire.Context,
    keychain: seed.Keychain,
    outputs_list: HashBuilderList,
    outputs_count: int,
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    """Read, validate, confirm and serialize the outputs, return the total non-change output amount."""
    total_amount = 0
    for _ in range(outputs_count):
        output: CardanoTxOutput = await ctx.call(CardanoTxItemAck(), CardanoTxOutput)
        _validate_output(output, protocol_magic, network_id, account_path_checker)
        if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
            await _show_output(
                ctx,
                keychain,
                output,
                signing_mode,
                protocol_magic,
                network_id,
            )

        output_address = _get_output_address(
            keychain, protocol_magic, network_id, output
        )

        if output.asset_groups_count == 0:
            outputs_list.append((output_address, output.amount))
        else:
            # output structure is: [address, [amount, asset_groups]]
            output_list: HashBuilderList = HashBuilderList(2)
            with outputs_list.append(output_list):
                output_list.append(output_address)
                output_value_list: HashBuilderList = HashBuilderList(2)
                with output_list.append(output_value_list):
                    output_value_list.append(output.amount)
                    asset_groups_dict: HashBuilderDict[
                        bytes, HashBuilderDict[bytes, int]
                    ] = HashBuilderDict(output.asset_groups_count)
                    with output_value_list.append(asset_groups_dict):
                        await _process_asset_groups(
                            ctx,
                            asset_groups_dict,
                            output.asset_groups_count,
                            _should_show_tokens(output, signing_mode),
                        )

        total_amount += output.amount

    if total_amount > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Total transaction amount is out of range!")


async def _process_asset_groups(
    ctx: wire.Context,
    asset_groups_dict: HashBuilderDict[bytes, HashBuilderDict[bytes, int]],
    asset_groups_count: int,
    should_show_tokens: bool,
) -> None:
    """Read, validate and serialize the asset groups of an output."""
    # until the CIP with canonical CBOR is finalized storing the seen_policy_ids is the only way we can check for
    # duplicate policy_ids
    seen_policy_ids: set[bytes] = set()
    for _ in range(asset_groups_count):
        asset_group: CardanoAssetGroup = await ctx.call(
            CardanoTxItemAck(), CardanoAssetGroup
        )
        asset_group.policy_id = bytes(asset_group.policy_id)
        _validate_asset_group(asset_group, seen_policy_ids)
        seen_policy_ids.add(asset_group.policy_id)

        tokens: HashBuilderDict[bytes, int] = HashBuilderDict(asset_group.tokens_count)
        with asset_groups_dict.add(asset_group.policy_id, tokens):
            await _process_tokens(
                ctx,
                tokens,
                asset_group.policy_id,
                asset_group.tokens_count,
                should_show_tokens,
            )


async def _process_tokens(
    ctx: wire.Context,
    tokens_dict: HashBuilderDict[bytes, int],
    policy_id: bytes,
    tokens_count: int,
    should_show_tokens: bool,
) -> None:
    """Read, validate, confirm and serialize the tokens of an asset group."""
    # until the CIP with canonical CBOR is finalized storing the seen_asset_name_bytes is the only way we can check for
    # duplicate tokens
    seen_asset_name_bytes: set[bytes] = set()
    for _ in range(tokens_count):
        token: CardanoToken = await ctx.call(CardanoTxItemAck(), CardanoToken)
        token.asset_name_bytes = bytes(token.asset_name_bytes)
        _validate_token(token, seen_asset_name_bytes)
        seen_asset_name_bytes.add(token.asset_name_bytes)
        if should_show_tokens:
            await confirm_sending_token(ctx, policy_id, token)

        tokens_dict.add(token.asset_name_bytes, token.amount)


async def _process_certificates(
    ctx: wire.Context,
    keychain: seed.Keychain,
    certificates_list: HashBuilderList,
    certificates_count: int,
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    """Read, validate, confirm and serialize the certificates."""
    if certificates_count == 0:
        return

    for _ in range(certificates_count):
        certificate: CardanoTxCertificate = await ctx.call(
            CardanoTxItemAck(), CardanoTxCertificate
        )
        validate_certificate(
            certificate, signing_mode, protocol_magic, network_id, account_path_checker
        )
        await _show_certificate(ctx, certificate, signing_mode)

        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            pool_parameters = certificate.pool_parameters
            assert pool_parameters is not None  # validate_certificate

            pool_items_list: HashBuilderList = HashBuilderList(
                POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT
            )
            with certificates_list.append(pool_items_list):
                for item in cborize_initial_pool_registration_certificate_fields(
                    certificate
                ):
                    pool_items_list.append(item)

                pool_owners_list: HashBuilderList[bytes] = HashBuilderList(
                    pool_parameters.owners_count
                )
                with pool_items_list.append(pool_owners_list):
                    await _process_pool_owners(
                        ctx,
                        keychain,
                        pool_owners_list,
                        pool_parameters.owners_count,
                        network_id,
                        account_path_checker,
                    )

                relays_list: HashBuilderList[cbor.CborSequence] = HashBuilderList(
                    pool_parameters.relays_count
                )
                with pool_items_list.append(relays_list):
                    await _process_pool_relays(
                        ctx, relays_list, pool_parameters.relays_count
                    )

                pool_items_list.append(cborize_pool_metadata(pool_parameters.metadata))
        else:
            certificates_list.append(cborize_certificate(keychain, certificate))


async def _process_pool_owners(
    ctx: wire.Context,
    keychain: seed.Keychain,
    pool_owners_list: HashBuilderList[bytes],
    owners_count: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    owners_as_path_count = 0
    for _ in range(owners_count):
        owner: CardanoPoolOwner = await ctx.call(CardanoTxItemAck(), CardanoPoolOwner)
        validate_pool_owner(owner, account_path_checker)
        await _show_pool_owner(ctx, keychain, owner, network_id)

        pool_owners_list.append(cborize_pool_owner(keychain, owner))

        if owner.staking_key_path:
            owners_as_path_count += 1

    assert_certificate_cond(owners_as_path_count == 1)


async def _process_pool_relays(
    ctx: wire.Context,
    relays_list: HashBuilderList[cbor.CborSequence],
    relays_count: int,
) -> None:
    for _ in range(relays_count):
        relay: CardanoPoolRelayParameters = await ctx.call(
            CardanoTxItemAck(), CardanoPoolRelayParameters
        )
        validate_pool_relay(relay)
        relays_list.append(cborize_pool_relay(relay))


async def _process_withdrawals(
    ctx: wire.Context,
    keychain: seed.Keychain,
    withdrawals_dict: HashBuilderDict[bytes, int],
    withdrawals_count: int,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    """Read, validate, confirm and serialize the withdrawals."""
    if withdrawals_count == 0:
        return

    # until the CIP with canonical CBOR is finalized storing the seen_withdrawals is the only way we can check for
    # duplicate withdrawals
    seen_withdrawals: set[tuple[int, ...]] = set()
    for _ in range(withdrawals_count):
        withdrawal: CardanoTxWithdrawal = await ctx.call(
            CardanoTxItemAck(), CardanoTxWithdrawal
        )
        _validate_withdrawal(withdrawal, seen_withdrawals, account_path_checker)
        await confirm_withdrawal(ctx, withdrawal)
        reward_address = derive_address_bytes(
            keychain,
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD,
                address_n=withdrawal.path,
            ),
            protocol_magic,
            network_id,
        )

        withdrawals_dict.add(reward_address, withdrawal.amount)


async def _process_auxiliary_data(
    ctx: wire.Context,
    keychain: seed.Keychain,
    tx_body_builder_dict: HashBuilderDict,
    protocol_magic: int,
    network_id: int,
) -> None:
    """Read, validate, confirm and serialize the auxiliary data."""
    auxiliary_data: CardanoTxAuxiliaryData = await ctx.call(
        CardanoTxItemAck(), CardanoTxAuxiliaryData
    )
    validate_auxiliary_data(auxiliary_data)

    (
        auxiliary_data_hash,
        auxiliary_data_supplement,
    ) = get_auxiliary_data_hash_and_supplement(
        keychain, auxiliary_data, protocol_magic, network_id
    )

    await show_auxiliary_data(
        ctx,
        keychain,
        auxiliary_data_hash,
        auxiliary_data.catalyst_registration_parameters,
        protocol_magic,
        network_id,
    )

    tx_body_builder_dict.add(TX_BODY_KEY_AUXILIARY_DATA, auxiliary_data_hash)

    await ctx.call(auxiliary_data_supplement, CardanoTxHostAck)


async def _process_witness_requests(
    ctx: wire.Context,
    keychain: seed.Keychain,
    tx_hash: bytes,
    witness_requests_count: int,
    signing_mode: CardanoTxSigningMode,
    account_path_checker: AccountPathChecker,
) -> CardanoTxResponseType:
    response: CardanoTxResponseType = CardanoTxItemAck()
    for _ in range(witness_requests_count):
        witness_request = await ctx.call(response, CardanoTxWitnessRequest)
        _validate_witness_request(witness_request, signing_mode, account_path_checker)
        await _show_witness(ctx, witness_request.path)

        response = (
            _get_byron_witness(keychain, witness_request.path, tx_hash)
            if is_byron_path(witness_request.path)
            else _get_shelley_witness(keychain, witness_request.path, tx_hash)
        )
    return response


def _get_byron_witness(
    keychain: seed.Keychain,
    path: list[int],
    tx_hash: bytes,
) -> CardanoTxWitnessResponse:
    node = keychain.derive(path)
    return CardanoTxWitnessResponse(
        type=CardanoTxWitnessType.BYRON_WITNESS,
        pub_key=derive_public_key(keychain, path),
        signature=_sign_tx_hash(keychain, tx_hash, path),
        chain_code=node.chain_code(),
    )


def _get_shelley_witness(
    keychain: seed.Keychain,
    path: list[int],
    tx_hash: bytes,
) -> CardanoTxWitnessResponse:
    return CardanoTxWitnessResponse(
        type=CardanoTxWitnessType.SHELLEY_WITNESS,
        pub_key=derive_public_key(keychain, path),
        signature=_sign_tx_hash(keychain, tx_hash, path),
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


def _validate_stake_pool_registration_tx_structure(msg: CardanoSignTxInit) -> None:
    """Ensure that there is exactly one certificate, which is stake pool registration, and no withdrawals"""
    if (
        msg.certificates_count != 1
        or msg.signing_mode != CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER
        or msg.withdrawals_count != 0
    ):
        raise INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE


def _validate_output(
    output: CardanoTxOutput,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    if output.address_parameters and output.address is not None:
        raise INVALID_OUTPUT

    if output.address_parameters:
        validate_address_parameters(output.address_parameters)
    elif output.address is not None:
        validate_output_address(output.address, protocol_magic, network_id)
    else:
        raise INVALID_OUTPUT

    account_path_checker.add_output(output)


async def _show_output(
    ctx: wire.Context,
    keychain: seed.Keychain,
    output: CardanoTxOutput,
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
) -> None:
    if output.address_parameters:
        await _fail_or_warn_if_invalid_path(
            ctx,
            SCHEMA_PAYMENT,
            output.address_parameters.address_n,
            CHANGE_OUTPUT_PATH_NAME,
        )

        await _show_change_output_staking_warnings(
            ctx, keychain, output.address_parameters, output.amount
        )

        if _should_hide_output(output.address_parameters.address_n):
            return

        address = derive_human_readable_address(
            keychain, output.address_parameters, protocol_magic, network_id
        )
    else:
        assert output.address is not None  # _validate_output
        address = output.address

    if output.asset_groups_count > 0:
        await show_warning_tx_output_contains_tokens(ctx)

    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        await confirm_sending(ctx, output.amount, address)


def _validate_asset_group(
    asset_group: CardanoAssetGroup, seen_policy_ids: set[bytes]
) -> None:
    if len(asset_group.policy_id) != MINTING_POLICY_ID_LENGTH:
        raise INVALID_TOKEN_BUNDLE_OUTPUT
    if asset_group.tokens_count == 0:
        raise INVALID_TOKEN_BUNDLE_OUTPUT
    if asset_group.policy_id in seen_policy_ids:
        raise INVALID_TOKEN_BUNDLE_OUTPUT


def _validate_token(token: CardanoToken, seen_asset_name_bytes: set[bytes]) -> None:
    if len(token.asset_name_bytes) > MAX_ASSET_NAME_LENGTH:
        raise INVALID_TOKEN_BUNDLE_OUTPUT
    if token.asset_name_bytes in seen_asset_name_bytes:
        raise INVALID_TOKEN_BUNDLE_OUTPUT


async def _show_certificate(
    ctx: wire.Context,
    certificate: CardanoTxCertificate,
    signing_mode: CardanoTxSigningMode,
) -> None:
    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        await _fail_or_warn_if_invalid_path(
            ctx, SCHEMA_STAKING, certificate.path, CERTIFICATE_PATH_NAME
        )
        await confirm_certificate(ctx, certificate)
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await _show_stake_pool_registration_certificate(ctx, certificate)


def _validate_withdrawal(
    withdrawal: CardanoTxWithdrawal,
    seen_withdrawals: set[tuple[int, ...]],
    account_path_checker: AccountPathChecker,
) -> None:
    if not SCHEMA_STAKING_ANY_ACCOUNT.match(withdrawal.path):
        raise INVALID_WITHDRAWAL

    if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
        raise INVALID_WITHDRAWAL

    path_tuple = tuple(withdrawal.path)
    if path_tuple in seen_withdrawals:
        raise wire.ProcessError("Duplicate withdrawals")
    else:
        seen_withdrawals.add(path_tuple)

    account_path_checker.add_withdrawal(withdrawal)


def _get_output_address(
    keychain: seed.Keychain,
    protocol_magic: int,
    network_id: int,
    output: CardanoTxOutput,
) -> bytes:
    if output.address_parameters:
        return derive_address_bytes(
            keychain, output.address_parameters, protocol_magic, network_id
        )
    else:
        assert output.address is not None  # _validate_output
        return get_address_bytes_unsafe(output.address)


def _sign_tx_hash(
    keychain: seed.Keychain, tx_body_hash: bytes, path: list[int]
) -> bytes:
    node = keychain.derive(path)
    return ed25519.sign_ext(node.private_key(), node.private_key_ext(), tx_body_hash)


async def _show_stake_pool_registration_certificate(
    ctx: wire.Context, stake_pool_registration_certificate: CardanoTxCertificate
) -> None:
    pool_parameters = stake_pool_registration_certificate.pool_parameters
    # _validate_stake_pool_registration_tx_structure ensures that there is only one
    # certificate, and validate_certificate ensures that the structure is valid
    assert pool_parameters is not None

    # display the transaction (certificate) in UI
    await confirm_stake_pool_parameters(ctx, pool_parameters)

    await confirm_stake_pool_metadata(ctx, pool_parameters.metadata)


async def _show_pool_owner(
    ctx: wire.Context, keychain: seed.Keychain, owner: CardanoPoolOwner, network_id: int
) -> None:
    if owner.staking_key_path:
        await _fail_or_warn_if_invalid_path(
            ctx,
            SCHEMA_STAKING,
            owner.staking_key_path,
            POOL_OWNER_STAKING_PATH_NAME,
        )

    await confirm_stake_pool_owner(ctx, keychain, owner, network_id)


def _validate_witness_request(
    witness_request: CardanoTxWitnessRequest,
    signing_mode: CardanoTxSigningMode,
    account_path_checker: AccountPathChecker,
) -> None:
    # witness path validation happens in _show_witness

    if signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        _ensure_no_payment_witness(witness_request)

    account_path_checker.add_witness_request(witness_request)


def _ensure_no_payment_witness(witness: CardanoTxWitnessRequest) -> None:
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
    if not SCHEMA_STAKING_ANY_ACCOUNT.match(witness.path):
        raise INVALID_STAKEPOOL_REGISTRATION_TX_WITNESSES


async def _show_witness(
    ctx: wire.Context,
    witness_path: list[int],
) -> None:
    if not SCHEMA_PAYMENT.match(witness_path) and not SCHEMA_STAKING.match(
        witness_path
    ):
        await _fail_or_warn_path(
            ctx,
            witness_path,
            WITNESS_PATH_NAME,
        )


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


def _should_hide_output(path: list[int]) -> bool:
    """Return whether the output address is from a safe path, so it could be hidden."""
    return SCHEMA_PAYMENT.match(path)


def _should_show_tokens(
    output: CardanoTxOutput, signing_mode: CardanoTxSigningMode
) -> bool:
    if signing_mode != CardanoTxSigningMode.ORDINARY_TRANSACTION:
        return False

    if output.address_parameters:
        return not _should_hide_output(output.address_parameters.address_n)

    return True


def _is_network_id_verifiable(msg: CardanoSignTxInit) -> bool:
    """
    checks whether there is at least one element that contains
    information about network ID, otherwise Trezor cannot
    guarantee that the tx is actually meant for the given network
    """
    return (
        msg.outputs_count != 0
        or msg.withdrawals_count != 0
        or msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER
    )


async def _fail_or_warn_if_invalid_path(
    ctx: wire.Context, schema: PathSchema, path: list[int], path_name: str
) -> None:
    if not schema.match(path):
        await _fail_or_warn_path(ctx, path, path_name)


async def _fail_or_warn_path(
    ctx: wire.Context, path: list[int], path_name: str
) -> None:
    if safety_checks.is_strict():
        raise wire.DataError("Invalid %s" % path_name.lower())
    else:
        await show_warning_path(ctx, path, path_name)
