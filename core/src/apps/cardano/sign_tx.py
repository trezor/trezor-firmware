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
    CardanoTxMint,
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
    validate_output_address,
    validate_output_address_parameters,
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
    INVALID_TOKEN_BUNDLE_MINT,
    INVALID_TOKEN_BUNDLE_OUTPUT,
    INVALID_TX_SIGNING_REQUEST,
    INVALID_WITHDRAWAL,
    INVALID_WITNESS_REQUEST,
    LOVELACE_MAX_SUPPLY,
    network_ids,
    protocol_magics,
)
from .helpers.account_path_check import AccountPathChecker
from .helpers.credential import Credential, should_show_address_credentials
from .helpers.hash_builder_collection import HashBuilderDict, HashBuilderList
from .helpers.paths import (
    CERTIFICATE_PATH_NAME,
    CHANGE_OUTPUT_PATH_NAME,
    CHANGE_OUTPUT_STAKING_PATH_NAME,
    POOL_OWNER_STAKING_PATH_NAME,
    SCHEMA_MINT,
    SCHEMA_PAYMENT,
    SCHEMA_STAKING,
    SCHEMA_STAKING_ANY_ACCOUNT,
    WITNESS_PATH_NAME,
)
from .helpers.utils import derive_public_key, validate_stake_credential
from .layout import (
    confirm_certificate,
    confirm_sending,
    confirm_sending_token,
    confirm_stake_pool_metadata,
    confirm_stake_pool_owner,
    confirm_stake_pool_parameters,
    confirm_stake_pool_registration_final,
    confirm_token_minting,
    confirm_transaction,
    confirm_withdrawal,
    confirm_witness_request,
    show_credentials,
    show_transaction_signing_mode,
    show_warning_path,
    show_warning_tx_contains_mint,
    show_warning_tx_network_unverifiable,
    show_warning_tx_output_contains_tokens,
)
from .seed import is_byron_path, is_multisig_path, is_shelley_path

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
TX_BODY_KEY_MINT = const(9)

POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT = 10


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTxInit, keychain: seed.Keychain
) -> CardanoSignTxFinished:
    is_network_id_verifiable = await _validate_tx_signing_request(ctx, msg)

    await show_transaction_signing_mode(ctx, msg.signing_mode)

    # inputs, outputs and fee are mandatory fields, count the number of optional fields present
    tx_body_map_item_count = 3 + sum(
        (
            msg.ttl is not None,
            msg.certificates_count > 0,
            msg.withdrawals_count > 0,
            msg.has_auxiliary_data,
            msg.validity_interval_start is not None,
            msg.minting_asset_groups_count > 0,
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
            msg.minting_asset_groups_count > 0,
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
    elif msg.signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        if not is_network_id_verifiable:
            await show_warning_tx_network_unverifiable(ctx)
    else:
        raise INVALID_TX_SIGNING_REQUEST

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
                msg.signing_mode,
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

    if msg.minting_asset_groups_count > 0:
        minting_dict: HashBuilderDict[bytes, HashBuilderDict] = HashBuilderDict(
            msg.minting_asset_groups_count
        )
        with tx_dict.add(TX_BODY_KEY_MINT, minting_dict):
            await _process_minting(ctx, minting_dict)


async def _confirm_transaction(
    ctx: wire.Context,
    msg: CardanoSignTxInit,
    is_network_id_verifiable: bool,
) -> None:
    if msg.signing_mode in (
        CardanoTxSigningMode.ORDINARY_TRANSACTION,
        CardanoTxSigningMode.MULTISIG_TRANSACTION,
    ):
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
    else:
        raise ValueError


async def _process_inputs(
    ctx: wire.Context,
    inputs_list: HashBuilderList[tuple[bytes, int]],
    inputs_count: int,
) -> None:
    """Read, validate and serialize the inputs."""
    for _ in range(inputs_count):
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
        _validate_output(
            output,
            signing_mode,
            protocol_magic,
            network_id,
            account_path_checker,
        )

        should_show_output = _should_show_output(output, signing_mode)
        if should_show_output:
            await _show_output(
                ctx,
                keychain,
                output,
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
                            should_show_output,
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
        _validate_token(token, seen_asset_name_bytes)
        seen_asset_name_bytes.add(token.asset_name_bytes)
        if should_show_tokens:
            await confirm_sending_token(ctx, policy_id, token)

        assert token.amount is not None  # _validate_token
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
                        protocol_magic,
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
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    owners_as_path_count = 0
    for _ in range(owners_count):
        owner: CardanoPoolOwner = await ctx.call(CardanoTxItemAck(), CardanoPoolOwner)
        validate_pool_owner(owner, account_path_checker)
        await _show_pool_owner(ctx, keychain, owner, protocol_magic, network_id)

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
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    """Read, validate, confirm and serialize the withdrawals."""
    if withdrawals_count == 0:
        return

    # until the CIP with canonical CBOR is finalized storing the seen_withdrawals is the only way we can check for
    # duplicate withdrawals
    seen_withdrawals: set[tuple[int, ...] | bytes] = set()
    for _ in range(withdrawals_count):
        withdrawal: CardanoTxWithdrawal = await ctx.call(
            CardanoTxItemAck(), CardanoTxWithdrawal
        )
        _validate_withdrawal(
            withdrawal, seen_withdrawals, signing_mode, account_path_checker
        )
        await confirm_withdrawal(ctx, withdrawal)
        reward_address_type = (
            CardanoAddressType.REWARD
            if withdrawal.path
            else CardanoAddressType.REWARD_SCRIPT
        )
        reward_address = derive_address_bytes(
            keychain,
            CardanoAddressParametersType(
                address_type=reward_address_type,
                address_n_staking=withdrawal.path,
                script_staking_hash=withdrawal.script_hash,
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


async def _process_minting(
    ctx: wire.Context, minting_dict: HashBuilderDict[bytes, HashBuilderDict]
) -> None:
    """Read, validate and serialize the asset groups of token minting."""
    token_minting: CardanoTxMint = await ctx.call(CardanoTxItemAck(), CardanoTxMint)

    await show_warning_tx_contains_mint(ctx)

    # until the CIP with canonical CBOR is finalized storing the seen_policy_ids is the only way we can check for
    # duplicate policy_ids
    seen_policy_ids: set[bytes] = set()
    for _ in range(token_minting.asset_groups_count):
        asset_group: CardanoAssetGroup = await ctx.call(
            CardanoTxItemAck(), CardanoAssetGroup
        )
        _validate_asset_group(asset_group, seen_policy_ids, is_mint=True)
        seen_policy_ids.add(asset_group.policy_id)

        tokens: HashBuilderDict[bytes, int] = HashBuilderDict(asset_group.tokens_count)
        with minting_dict.add(asset_group.policy_id, tokens):
            await _process_minting_tokens(
                ctx,
                tokens,
                asset_group.policy_id,
                asset_group.tokens_count,
            )


async def _process_minting_tokens(
    ctx: wire.Context,
    tokens: HashBuilderDict[bytes, int],
    policy_id: bytes,
    tokens_count: int,
) -> None:
    """Read, validate, confirm and serialize the tokens of an asset group."""
    # until the CIP with canonical CBOR is finalized storing the seen_asset_name_bytes is the only way we can check for
    # duplicate tokens
    seen_asset_name_bytes: set[bytes] = set()
    for _ in range(tokens_count):
        token: CardanoToken = await ctx.call(CardanoTxItemAck(), CardanoToken)
        _validate_token(token, seen_asset_name_bytes, is_mint=True)
        seen_asset_name_bytes.add(token.asset_name_bytes)
        await confirm_token_minting(ctx, policy_id, token)

        assert token.mint_amount is not None  # _validate_token
        tokens.add(token.asset_name_bytes, token.mint_amount)


async def _process_witness_requests(
    ctx: wire.Context,
    keychain: seed.Keychain,
    tx_hash: bytes,
    witness_requests_count: int,
    signing_mode: CardanoTxSigningMode,
    transaction_has_token_minting: bool,
    account_path_checker: AccountPathChecker,
) -> CardanoTxResponseType:
    response: CardanoTxResponseType = CardanoTxItemAck()

    for _ in range(witness_requests_count):
        witness_request = await ctx.call(response, CardanoTxWitnessRequest)
        _validate_witness_request(
            witness_request,
            signing_mode,
            transaction_has_token_minting,
            account_path_checker,
        )
        path = witness_request.path
        await _show_witness_request(ctx, path, signing_mode)
        if is_byron_path(path):
            response = _get_byron_witness(keychain, path, tx_hash)
        else:
            response = _get_shelley_witness(keychain, path, tx_hash)

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
        or msg.minting_asset_groups_count != 0
    ):
        raise INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE


def _validate_output(
    output: CardanoTxOutput,
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    if output.address_parameters and output.address is not None:
        raise INVALID_OUTPUT

    if address_parameters := output.address_parameters:
        if signing_mode != CardanoTxSigningMode.ORDINARY_TRANSACTION:
            raise INVALID_OUTPUT

        validate_output_address_parameters(address_parameters)
        _fail_if_strict_and_unusual(address_parameters)
    elif output.address is not None:
        validate_output_address(output.address, protocol_magic, network_id)
    else:
        raise INVALID_OUTPUT

    account_path_checker.add_output(output)


def _should_show_output(
    output: CardanoTxOutput,
    signing_mode: CardanoTxSigningMode,
) -> bool:
    if signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        # In a pool registration transaction, there are no inputs belonging to the user
        # and no spending witnesses. It is thus safe to not show the outputs.
        return False

    if output.address_parameters:  # is change output
        if not should_show_address_credentials(output.address_parameters):
            # we don't need to display simple address outputs
            return False

    return True


async def _show_output(
    ctx: wire.Context,
    keychain: seed.Keychain,
    output: CardanoTxOutput,
    protocol_magic: int,
    network_id: int,
) -> None:
    if output.asset_groups_count > 0:
        await show_warning_tx_output_contains_tokens(ctx)

    is_change_output: bool
    if address_parameters := output.address_parameters:
        is_change_output = True

        await show_credentials(
            ctx,
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
            is_change_output=True,
        )

        address = derive_human_readable_address(
            keychain, address_parameters, protocol_magic, network_id
        )
    else:
        is_change_output = False

        assert output.address is not None  # _validate_output
        address = output.address

    await confirm_sending(ctx, output.amount, address, is_change_output)


def _validate_asset_group(
    asset_group: CardanoAssetGroup, seen_policy_ids: set[bytes], is_mint: bool = False
) -> None:
    INVALID_TOKEN_BUNDLE = (
        INVALID_TOKEN_BUNDLE_MINT if is_mint else INVALID_TOKEN_BUNDLE_OUTPUT
    )

    if len(asset_group.policy_id) != MINTING_POLICY_ID_LENGTH:
        raise INVALID_TOKEN_BUNDLE
    if asset_group.tokens_count == 0:
        raise INVALID_TOKEN_BUNDLE
    if asset_group.policy_id in seen_policy_ids:
        raise INVALID_TOKEN_BUNDLE


def _validate_token(
    token: CardanoToken, seen_asset_name_bytes: set[bytes], is_mint: bool = False
) -> None:
    INVALID_TOKEN_BUNDLE = (
        INVALID_TOKEN_BUNDLE_MINT if is_mint else INVALID_TOKEN_BUNDLE_OUTPUT
    )

    if is_mint:
        if token.mint_amount is None or token.amount is not None:
            raise INVALID_TOKEN_BUNDLE
    else:
        if token.amount is None or token.mint_amount is not None:
            raise INVALID_TOKEN_BUNDLE

    if len(token.asset_name_bytes) > MAX_ASSET_NAME_LENGTH:
        raise INVALID_TOKEN_BUNDLE
    if token.asset_name_bytes in seen_asset_name_bytes:
        raise INVALID_TOKEN_BUNDLE


async def _show_certificate(
    ctx: wire.Context,
    certificate: CardanoTxCertificate,
    signing_mode: CardanoTxSigningMode,
) -> None:
    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        assert certificate.path  # validate_certificate
        await _fail_or_warn_if_invalid_path(
            ctx, SCHEMA_STAKING, certificate.path, CERTIFICATE_PATH_NAME
        )
        await confirm_certificate(ctx, certificate)
    elif signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        assert certificate.script_hash  # validate_certificate
        await confirm_certificate(ctx, certificate)
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await _show_stake_pool_registration_certificate(ctx, certificate)


def _validate_withdrawal(
    withdrawal: CardanoTxWithdrawal,
    seen_withdrawals: set[tuple[int, ...] | bytes],
    signing_mode: CardanoTxSigningMode,
    account_path_checker: AccountPathChecker,
) -> None:
    validate_stake_credential(
        withdrawal.path, withdrawal.script_hash, signing_mode, INVALID_WITHDRAWAL
    )

    if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
        raise INVALID_WITHDRAWAL

    credential = tuple(withdrawal.path) if withdrawal.path else withdrawal.script_hash
    assert credential  # validate_stake_credential

    if credential in seen_withdrawals:
        raise wire.ProcessError("Duplicate withdrawals")
    else:
        seen_withdrawals.add(credential)

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
    ctx: wire.Context,
    keychain: seed.Keychain,
    owner: CardanoPoolOwner,
    protocol_magic: int,
    network_id: int,
) -> None:
    if owner.staking_key_path:
        await _fail_or_warn_if_invalid_path(
            ctx,
            SCHEMA_STAKING,
            owner.staking_key_path,
            POOL_OWNER_STAKING_PATH_NAME,
        )

    await confirm_stake_pool_owner(ctx, keychain, owner, protocol_magic, network_id)


def _validate_witness_request(
    witness_request: CardanoTxWitnessRequest,
    signing_mode: CardanoTxSigningMode,
    transaction_has_token_minting: bool,
    account_path_checker: AccountPathChecker,
) -> None:
    # further witness path validation happens in _show_witness_request
    is_minting = SCHEMA_MINT.match(witness_request.path)

    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        if not (
            is_byron_path(witness_request.path)
            or is_shelley_path(witness_request.path)
            or is_minting
        ):
            raise INVALID_WITNESS_REQUEST
        if is_minting and not transaction_has_token_minting:
            raise INVALID_WITNESS_REQUEST
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        _ensure_only_staking_witnesses(witness_request)
    elif signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        if not is_multisig_path(witness_request.path) and not is_minting:
            raise INVALID_WITNESS_REQUEST
        if is_minting and not transaction_has_token_minting:
            raise INVALID_WITNESS_REQUEST

    account_path_checker.add_witness_request(witness_request)


def _ensure_only_staking_witnesses(witness: CardanoTxWitnessRequest) -> None:
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


async def _show_witness_request(
    ctx: wire.Context,
    witness_path: list[int],
    signing_mode: CardanoTxSigningMode,
) -> None:
    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        # In an ordinary transaction we only allow payment, staking or minting paths.
        # If the path is an unusual payment or staking path, we either fail or show the path to the user
        # depending on Trezor's configuration. If it's a minting path, we always show it.
        is_payment = SCHEMA_PAYMENT.match(witness_path)
        is_staking = SCHEMA_STAKING.match(witness_path)
        is_minting = SCHEMA_MINT.match(witness_path)

        if is_minting:
            await confirm_witness_request(ctx, witness_path)
        elif not is_payment and not is_staking:
            await _fail_or_warn_path(ctx, witness_path, WITNESS_PATH_NAME)
    elif signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        await confirm_witness_request(ctx, witness_path)
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await confirm_witness_request(ctx, witness_path)


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
        raise wire.DataError(f"Invalid {path_name.lower()}")
    else:
        await show_warning_path(ctx, path, path_name)


def _fail_if_strict_and_unusual(
    address_parameters: CardanoAddressParametersType,
) -> None:
    if not safety_checks.is_strict():
        return

    if Credential.payment_credential(address_parameters).is_unusual_path:
        raise wire.DataError(f"Invalid {CHANGE_OUTPUT_PATH_NAME.lower()}")

    if Credential.stake_credential(address_parameters).is_unusual_path:
        raise wire.DataError(f"Invalid {CHANGE_OUTPUT_STAKING_PATH_NAME.lower()}")
