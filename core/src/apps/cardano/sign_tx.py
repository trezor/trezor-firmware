from micropython import const
from typing import TYPE_CHECKING

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
    CardanoTxCollateralInput,
    CardanoTxHostAck,
    CardanoTxInput,
    CardanoTxItemAck,
    CardanoTxMint,
    CardanoTxOutput,
    CardanoTxRequiredSigner,
    CardanoTxWithdrawal,
    CardanoTxWitnessRequest,
    CardanoTxWitnessResponse,
)

from apps.common import cbor, safety_checks

from . import seed
from .address import (
    ADDRESS_TYPES_PAYMENT_SCRIPT,
    derive_address_bytes,
    derive_human_readable_address,
    get_address_bytes_unsafe,
    get_address_type,
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
    ADDRESS_KEY_HASH_SIZE,
    INPUT_PREV_HASH_SIZE,
    INVALID_COLLATERAL_INPUT,
    INVALID_INPUT,
    INVALID_OUTPUT,
    INVALID_OUTPUT_DATUM_HASH,
    INVALID_REQUIRED_SIGNER,
    INVALID_SCRIPT_DATA_HASH,
    INVALID_STAKE_POOL_REGISTRATION_TX_STRUCTURE,
    INVALID_STAKEPOOL_REGISTRATION_TX_WITNESSES,
    INVALID_TOKEN_BUNDLE_MINT,
    INVALID_TOKEN_BUNDLE_OUTPUT,
    INVALID_TX_SIGNING_REQUEST,
    INVALID_WITHDRAWAL,
    INVALID_WITNESS_REQUEST,
    LOVELACE_MAX_SUPPLY,
    OUTPUT_DATUM_HASH_SIZE,
    SCRIPT_DATA_HASH_SIZE,
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
from .helpers.utils import (
    derive_public_key,
    get_public_key_hash,
    validate_stake_credential,
)
from .layout import (
    confirm_certificate,
    confirm_collateral_input,
    confirm_input,
    confirm_required_signer,
    confirm_script_data_hash,
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
    show_change_output_credentials,
    show_device_owned_output_credentials,
    show_transaction_signing_mode,
    show_warning_no_collateral_inputs,
    show_warning_no_script_data_hash,
    show_warning_path,
    show_warning_tx_contains_mint,
    show_warning_tx_network_unverifiable,
    show_warning_tx_output_contains_datum_hash,
    show_warning_tx_output_contains_tokens,
    show_warning_tx_output_no_datum_hash,
)
from .seed import is_byron_path, is_minting_path, is_multisig_path, is_shelley_path

if TYPE_CHECKING:
    from typing import Any
    from apps.common.paths import PathSchema

    CardanoTxResponseType = CardanoTxItemAck | CardanoTxWitnessResponse

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
TX_BODY_KEY_SCRIPT_DATA_HASH = const(11)
TX_BODY_KEY_COLLATERAL_INPUTS = const(13)
TX_BODY_KEY_REQUIRED_SIGNERS = const(14)
TX_BODY_KEY_NETWORK_ID = const(15)

POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT = 10


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTxInit, keychain: seed.Keychain
) -> CardanoSignTxFinished:
    await show_transaction_signing_mode(ctx, msg.signing_mode)

    is_network_id_verifiable = await _validate_tx_signing_request(ctx, msg)

    # inputs, outputs and fee are mandatory fields, count the number of optional fields present
    tx_body_map_item_count = 3 + sum(
        (
            msg.ttl is not None,
            msg.certificates_count > 0,
            msg.withdrawals_count > 0,
            msg.has_auxiliary_data,
            msg.validity_interval_start is not None,
            msg.minting_asset_groups_count > 0,
            msg.include_network_id,
            msg.script_data_hash is not None,
            msg.collateral_inputs_count > 0,
            msg.required_signers_count > 0,
        )
    )

    account_path_checker = AccountPathChecker()

    hash_fn = hashlib.blake2b(outlen=32)
    tx_dict: HashBuilderDict[int, Any] = HashBuilderDict(
        tx_body_map_item_count, INVALID_TX_SIGNING_REQUEST
    )
    tx_dict.start(hash_fn)
    with tx_dict:
        await _process_transaction(ctx, msg, keychain, tx_dict, account_path_checker)

    tx_hash = hash_fn.digest()
    await _confirm_transaction(ctx, msg, is_network_id_verifiable, tx_hash)

    try:
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
    if not is_network_id_verifiable:
        await show_warning_tx_network_unverifiable(ctx)

    if msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        _validate_stake_pool_registration_tx_structure(msg)

    if msg.script_data_hash is not None and msg.signing_mode not in (
        CardanoTxSigningMode.ORDINARY_TRANSACTION,
        CardanoTxSigningMode.MULTISIG_TRANSACTION,
        CardanoTxSigningMode.PLUTUS_TRANSACTION,
    ):
        raise INVALID_TX_SIGNING_REQUEST

    if msg.signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        # these items should be present if a Plutus script should be executed
        if msg.script_data_hash is None:
            await show_warning_no_script_data_hash(ctx)
        if msg.collateral_inputs_count == 0:
            await show_warning_no_collateral_inputs(ctx)
    else:
        # these items are only allowed in PLUTUS_TRANSACTION
        if msg.collateral_inputs_count != 0 or msg.required_signers_count != 0:
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
        await _process_inputs(ctx, inputs_list, msg.inputs_count, msg.signing_mode)

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
            msg.withdrawals_count, INVALID_WITHDRAWAL
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
            msg.minting_asset_groups_count, INVALID_TOKEN_BUNDLE_MINT
        )
        with tx_dict.add(TX_BODY_KEY_MINT, minting_dict):
            await _process_minting(ctx, minting_dict)

    if msg.script_data_hash is not None:
        await _process_script_data_hash(ctx, tx_dict, msg.script_data_hash)

    if msg.collateral_inputs_count > 0:
        collateral_inputs_list: HashBuilderList[tuple[bytes, int]] = HashBuilderList(
            msg.collateral_inputs_count
        )
        with tx_dict.add(TX_BODY_KEY_COLLATERAL_INPUTS, collateral_inputs_list):
            await _process_collateral_inputs(
                ctx,
                collateral_inputs_list,
                msg.collateral_inputs_count,
            )

    if msg.required_signers_count > 0:
        required_signers_list: HashBuilderList[bytes] = HashBuilderList(
            msg.required_signers_count
        )
        with tx_dict.add(TX_BODY_KEY_REQUIRED_SIGNERS, required_signers_list):
            await _process_required_signers(
                ctx,
                keychain,
                required_signers_list,
                msg.required_signers_count,
            )

    if msg.include_network_id:
        tx_dict.add(TX_BODY_KEY_NETWORK_ID, msg.network_id)


async def _confirm_transaction(
    ctx: wire.Context,
    msg: CardanoSignTxInit,
    is_network_id_verifiable: bool,
    tx_hash: bytes,
) -> None:
    if msg.signing_mode in (
        CardanoTxSigningMode.ORDINARY_TRANSACTION,
        CardanoTxSigningMode.MULTISIG_TRANSACTION,
    ):
        await confirm_transaction(
            ctx,
            msg.fee,
            msg.network_id,
            msg.protocol_magic,
            msg.ttl,
            msg.validity_interval_start,
            is_network_id_verifiable,
            tx_hash=None,
        )
    elif msg.signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        # we display tx hash so that experienced users can compare it to the tx hash computed by
        # a trusted device (in case the tx contains many items which are tedious to check one by
        # one on the Trezor screen)
        await confirm_transaction(
            ctx,
            msg.fee,
            msg.network_id,
            msg.protocol_magic,
            msg.ttl,
            msg.validity_interval_start,
            is_network_id_verifiable,
            tx_hash,
        )
    elif msg.signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await confirm_stake_pool_registration_final(
            ctx, msg.protocol_magic, msg.ttl, msg.validity_interval_start
        )
    else:
        raise RuntimeError  # we didn't cover all signing modes


async def _process_inputs(
    ctx: wire.Context,
    inputs_list: HashBuilderList[tuple[bytes, int]],
    inputs_count: int,
    signing_mode: CardanoTxSigningMode,
) -> None:
    """Read, validate and serialize the inputs."""
    for _ in range(inputs_count):
        input: CardanoTxInput = await ctx.call(CardanoTxItemAck(), CardanoTxInput)
        _validate_input(input)
        if signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
            await confirm_input(ctx, input)

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
                signing_mode,
            )

        output_address = _get_output_address(
            keychain, protocol_magic, network_id, output
        )

        has_datum_hash = output.datum_hash is not None
        output_list: HashBuilderList = HashBuilderList(2 + int(has_datum_hash))
        with outputs_list.append(output_list):
            output_list.append(output_address)
            if output.asset_groups_count == 0:
                # output structure is: [address, amount, datum_hash?]
                output_list.append(output.amount)
            else:
                # output structure is: [address, [amount, asset_groups], datum_hash?]
                output_value_list: HashBuilderList = HashBuilderList(2)
                with output_list.append(output_value_list):
                    output_value_list.append(output.amount)
                    asset_groups_dict: HashBuilderDict[
                        bytes, HashBuilderDict[bytes, int]
                    ] = HashBuilderDict(
                        output.asset_groups_count, INVALID_TOKEN_BUNDLE_OUTPUT
                    )
                    with output_value_list.append(asset_groups_dict):
                        await _process_asset_groups(
                            ctx,
                            asset_groups_dict,
                            output.asset_groups_count,
                            should_show_output,
                        )
            if has_datum_hash:
                output_list.append(output.datum_hash)

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
    for _ in range(asset_groups_count):
        asset_group: CardanoAssetGroup = await ctx.call(
            CardanoTxItemAck(), CardanoAssetGroup
        )
        _validate_asset_group(asset_group)

        tokens: HashBuilderDict[bytes, int] = HashBuilderDict(
            asset_group.tokens_count, INVALID_TOKEN_BUNDLE_OUTPUT
        )
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
    for _ in range(tokens_count):
        token: CardanoToken = await ctx.call(CardanoTxItemAck(), CardanoToken)
        _validate_token(token)
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
    for _ in range(certificates_count):
        certificate: CardanoTxCertificate = await ctx.call(
            CardanoTxItemAck(), CardanoTxCertificate
        )
        validate_certificate(
            certificate, signing_mode, protocol_magic, network_id, account_path_checker
        )
        await _show_certificate(ctx, certificate, signing_mode, network_id)

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

    for _ in range(withdrawals_count):
        withdrawal: CardanoTxWithdrawal = await ctx.call(
            CardanoTxItemAck(), CardanoTxWithdrawal
        )
        _validate_withdrawal(
            withdrawal,
            signing_mode,
            account_path_checker,
        )
        reward_address_bytes = _derive_withdrawal_reward_address_bytes(
            keychain, withdrawal, protocol_magic, network_id
        )

        await confirm_withdrawal(ctx, withdrawal, reward_address_bytes, network_id)

        withdrawals_dict.add(reward_address_bytes, withdrawal.amount)


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

    for _ in range(token_minting.asset_groups_count):
        asset_group: CardanoAssetGroup = await ctx.call(
            CardanoTxItemAck(), CardanoAssetGroup
        )
        _validate_asset_group(asset_group, is_mint=True)

        tokens: HashBuilderDict[bytes, int] = HashBuilderDict(
            asset_group.tokens_count, INVALID_TOKEN_BUNDLE_MINT
        )
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
    for _ in range(tokens_count):
        token: CardanoToken = await ctx.call(CardanoTxItemAck(), CardanoToken)
        _validate_token(token, is_mint=True)
        await confirm_token_minting(ctx, policy_id, token)

        assert token.mint_amount is not None  # _validate_token
        tokens.add(token.asset_name_bytes, token.mint_amount)


async def _process_script_data_hash(
    ctx: wire.Context,
    tx_body_builder_dict: HashBuilderDict,
    script_data_hash: bytes,
) -> None:
    """Validate, confirm and serialize the script data hash."""
    _validate_script_data_hash(script_data_hash)

    await confirm_script_data_hash(ctx, script_data_hash)

    tx_body_builder_dict.add(TX_BODY_KEY_SCRIPT_DATA_HASH, script_data_hash)


async def _process_collateral_inputs(
    ctx: wire.Context,
    collateral_inputs_list: HashBuilderList[tuple[bytes, int]],
    collateral_inputs_count: int,
) -> None:
    """Read, validate, show and serialize the collateral inputs."""
    for _ in range(collateral_inputs_count):
        collateral_input: CardanoTxCollateralInput = await ctx.call(
            CardanoTxItemAck(), CardanoTxCollateralInput
        )
        _validate_collateral_input(collateral_input)
        await confirm_collateral_input(ctx, collateral_input)

        collateral_inputs_list.append(
            (collateral_input.prev_hash, collateral_input.prev_index)
        )


async def _process_required_signers(
    ctx: wire.Context,
    keychain: seed.Keychain,
    required_signers_list: HashBuilderList[bytes],
    required_signers_count: int,
) -> None:
    """Read, validate, show and serialize the required signers."""
    for _ in range(required_signers_count):
        required_signer: CardanoTxRequiredSigner = await ctx.call(
            CardanoTxItemAck(), CardanoTxRequiredSigner
        )
        _validate_required_signer(required_signer)
        await confirm_required_signer(ctx, required_signer)

        key_hash = required_signer.key_hash or get_public_key_hash(
            keychain, required_signer.key_path
        )

        required_signers_list.append(key_hash)


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


def _validate_input(input: CardanoTxInput) -> None:
    if len(input.prev_hash) != INPUT_PREV_HASH_SIZE:
        raise INVALID_INPUT


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
        if signing_mode not in (
            CardanoTxSigningMode.ORDINARY_TRANSACTION,
            CardanoTxSigningMode.PLUTUS_TRANSACTION,
        ):
            # Change outputs are allowed only in ORDINARY_TRANSACTION.
            # In PLUTUS_TRANSACTION, we display device-owned outputs similarly to change outputs.
            raise INVALID_OUTPUT

        validate_output_address_parameters(address_parameters)
        _fail_if_strict_and_unusual(address_parameters)
    elif output.address is not None:
        validate_output_address(output.address, protocol_magic, network_id)
    else:
        raise INVALID_OUTPUT

    if output.datum_hash is not None:
        if signing_mode not in (
            CardanoTxSigningMode.ORDINARY_TRANSACTION,
            CardanoTxSigningMode.MULTISIG_TRANSACTION,
            CardanoTxSigningMode.PLUTUS_TRANSACTION,
        ):
            raise INVALID_OUTPUT
        if len(output.datum_hash) != OUTPUT_DATUM_HASH_SIZE:
            raise INVALID_OUTPUT_DATUM_HASH
        address_type = _get_output_address_type(output)
        if address_type not in ADDRESS_TYPES_PAYMENT_SCRIPT:
            raise INVALID_OUTPUT

    account_path_checker.add_output(output)


def _should_show_output(
    output: CardanoTxOutput,
    signing_mode: CardanoTxSigningMode,
) -> bool:
    if output.datum_hash:
        # none of the reasons for hiding below should be reachable when datum hash
        # is present, but let's make sure
        return True

    address_type = _get_output_address_type(output)
    if output.datum_hash is None and address_type in ADDRESS_TYPES_PAYMENT_SCRIPT:
        # Plutus script address without a datum hash is unspendable, we must show a warning
        return True

    if signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        # In Plutus transactions, all outputs need to be shown (even device-owned), because they
        # might influence the script evaluation.
        return True

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
    signing_mode: CardanoTxSigningMode,
) -> None:
    if output.datum_hash:
        await show_warning_tx_output_contains_datum_hash(ctx, output.datum_hash)

    address_type = _get_output_address_type(output)
    if output.datum_hash is None and address_type in ADDRESS_TYPES_PAYMENT_SCRIPT:
        await show_warning_tx_output_no_datum_hash(ctx)

    if output.asset_groups_count > 0:
        await show_warning_tx_output_contains_tokens(ctx)

    is_change_output = False
    if address_parameters := output.address_parameters:
        address = derive_human_readable_address(
            keychain, address_parameters, protocol_magic, network_id
        )
        payment_credential = Credential.payment_credential(address_parameters)
        stake_credential = Credential.stake_credential(address_parameters)

        if signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
            show_both_credentials = should_show_address_credentials(address_parameters)
            # In ORDINARY_TRANSACTION, change outputs with matching payment and staking paths can
            # be hidden, but we need to show them in PLUTUS_TRANSACTION because of the script
            # evaluation. We at least hide the staking path if it matches the payment path.
            await show_device_owned_output_credentials(
                ctx,
                payment_credential,
                stake_credential,
                show_both_credentials,
            )
        else:
            is_change_output = True
            await show_change_output_credentials(
                ctx,
                payment_credential,
                stake_credential,
            )
    else:
        assert output.address is not None  # _validate_output
        address = output.address

    await confirm_sending(ctx, output.amount, address, is_change_output, network_id)


def _validate_asset_group(
    asset_group: CardanoAssetGroup, is_mint: bool = False
) -> None:
    INVALID_TOKEN_BUNDLE = (
        INVALID_TOKEN_BUNDLE_MINT if is_mint else INVALID_TOKEN_BUNDLE_OUTPUT
    )

    if len(asset_group.policy_id) != MINTING_POLICY_ID_LENGTH:
        raise INVALID_TOKEN_BUNDLE
    if asset_group.tokens_count == 0:
        raise INVALID_TOKEN_BUNDLE


def _validate_token(token: CardanoToken, is_mint: bool = False) -> None:
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


async def _show_certificate(
    ctx: wire.Context,
    certificate: CardanoTxCertificate,
    signing_mode: CardanoTxSigningMode,
    network_id: int,
) -> None:
    if signing_mode == CardanoTxSigningMode.ORDINARY_TRANSACTION:
        assert certificate.path  # validate_certificate
        await _fail_or_warn_if_invalid_path(
            ctx, SCHEMA_STAKING, certificate.path, CERTIFICATE_PATH_NAME
        )
        await confirm_certificate(ctx, certificate)
    elif signing_mode in (
        CardanoTxSigningMode.MULTISIG_TRANSACTION,
        CardanoTxSigningMode.PLUTUS_TRANSACTION,
    ):
        await confirm_certificate(ctx, certificate)
    elif signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER:
        await _show_stake_pool_registration_certificate(ctx, certificate, network_id)
    else:
        raise RuntimeError  # we didn't cover all signing modes


def _validate_withdrawal(
    withdrawal: CardanoTxWithdrawal,
    signing_mode: CardanoTxSigningMode,
    account_path_checker: AccountPathChecker,
) -> None:
    validate_stake_credential(
        withdrawal.path,
        withdrawal.script_hash,
        withdrawal.key_hash,
        signing_mode,
        INVALID_WITHDRAWAL,
    )

    if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
        raise INVALID_WITHDRAWAL

    account_path_checker.add_withdrawal(withdrawal)


def _validate_script_data_hash(script_data_hash: bytes) -> None:
    if len(script_data_hash) != SCRIPT_DATA_HASH_SIZE:
        raise INVALID_SCRIPT_DATA_HASH


def _validate_collateral_input(collateral_input: CardanoTxCollateralInput) -> None:
    if len(collateral_input.prev_hash) != INPUT_PREV_HASH_SIZE:
        raise INVALID_COLLATERAL_INPUT


def _validate_required_signer(required_signer: CardanoTxRequiredSigner) -> None:
    if required_signer.key_hash and required_signer.key_path:
        raise INVALID_REQUIRED_SIGNER

    if required_signer.key_hash:
        if len(required_signer.key_hash) != ADDRESS_KEY_HASH_SIZE:
            raise INVALID_REQUIRED_SIGNER
    elif required_signer.key_path:
        if not (
            is_shelley_path(required_signer.key_path)
            or is_multisig_path(required_signer.key_path)
            or is_minting_path(required_signer.key_path)
        ):
            raise INVALID_REQUIRED_SIGNER
    else:
        raise INVALID_REQUIRED_SIGNER


def _derive_withdrawal_reward_address_bytes(
    keychain: seed.Keychain,
    withdrawal: CardanoTxWithdrawal,
    protocol_magic: int,
    network_id: int,
) -> bytes:
    reward_address_type = (
        CardanoAddressType.REWARD
        if withdrawal.path or withdrawal.key_hash
        else CardanoAddressType.REWARD_SCRIPT
    )
    return derive_address_bytes(
        keychain,
        CardanoAddressParametersType(
            address_type=reward_address_type,
            address_n_staking=withdrawal.path,
            staking_key_hash=withdrawal.key_hash,
            script_staking_hash=withdrawal.script_hash,
        ),
        protocol_magic,
        network_id,
    )


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


def _get_output_address_type(output: CardanoTxOutput) -> CardanoAddressType:
    if output.address_parameters:
        return output.address_parameters.address_type
    assert output.address is not None  # _validate_output
    return get_address_type(get_address_bytes_unsafe(output.address))


def _sign_tx_hash(
    keychain: seed.Keychain, tx_body_hash: bytes, path: list[int]
) -> bytes:
    node = keychain.derive(path)
    return ed25519.sign_ext(node.private_key(), node.private_key_ext(), tx_body_hash)


async def _show_stake_pool_registration_certificate(
    ctx: wire.Context,
    stake_pool_registration_certificate: CardanoTxCertificate,
    network_id: int,
) -> None:
    pool_parameters = stake_pool_registration_certificate.pool_parameters
    # _validate_stake_pool_registration_tx_structure ensures that there is only one
    # certificate, and validate_certificate ensures that the structure is valid
    assert pool_parameters is not None

    # display the transaction (certificate) in UI
    await confirm_stake_pool_parameters(ctx, pool_parameters, network_id)

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
    elif signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        if not (
            is_shelley_path(witness_request.path)
            or is_multisig_path(witness_request.path)
            or is_minting
        ):
            raise INVALID_WITNESS_REQUEST
            # in PLUTUS_TRANSACTION, we allow minting witnesses even when transaction
            # doesn't have token minting
    else:
        raise RuntimeError  # we didn't cover all signing modes

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
    elif signing_mode in (
        CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
        CardanoTxSigningMode.MULTISIG_TRANSACTION,
        CardanoTxSigningMode.PLUTUS_TRANSACTION,
    ):
        await confirm_witness_request(ctx, witness_path)
    else:
        raise RuntimeError  # we didn't cover all signing modes


def _is_network_id_verifiable(msg: CardanoSignTxInit) -> bool:
    """
    Checks whether there is at least one element that contains
    information about network ID, otherwise Trezor cannot
    guarantee that the tx is actually meant for the given network.

    Note: Shelley addresses contain network id. The intended network
    of Byron addresses can be determined based on whether they
    contain the protocol magic. These checks are performed during
    address validation.
    """
    return (
        msg.include_network_id
        or msg.outputs_count != 0
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
