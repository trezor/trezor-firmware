from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
    CardanoNativeScriptHashDisplayFormat,
    CardanoNativeScriptType,
    CardanoTxSigningMode,
)
from trezor.messages import CardanoAddressParametersType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_blob,
    confirm_metadata,
    confirm_output,
    confirm_path_warning,
    confirm_properties,
    confirm_text,
    show_address,
)

from apps.common.paths import address_n_to_str

from . import seed
from .address import derive_human_readable_address, encode_human_readable_address
from .helpers import bech32, network_ids, protocol_magics
from .helpers.utils import (
    format_account_number,
    format_asset_fingerprint,
    format_optional_int,
    format_stake_pool_id,
    to_account_path,
)
from .seed import is_minting_path, is_multisig_path

if TYPE_CHECKING:
    from trezor import wire
    from trezor.messages import (
        CardanoNativeScript,
        CardanoTxCertificate,
        CardanoTxCollateralInput,
        CardanoTxInput,
        CardanoTxRequiredSigner,
        CardanoTxWithdrawal,
        CardanoPoolParametersType,
        CardanoPoolOwner,
        CardanoPoolMetadataType,
        CardanoToken,
    )

    from trezor.ui.layouts import PropertyType
    from .helpers.credential import Credential


ADDRESS_TYPE_NAMES = {
    CardanoAddressType.BYRON: "Legacy",
    CardanoAddressType.BASE: "Base",
    CardanoAddressType.BASE_SCRIPT_KEY: "Base",
    CardanoAddressType.BASE_KEY_SCRIPT: "Base",
    CardanoAddressType.BASE_SCRIPT_SCRIPT: "Base",
    CardanoAddressType.POINTER: "Pointer",
    CardanoAddressType.POINTER_SCRIPT: "Pointer",
    CardanoAddressType.ENTERPRISE: "Enterprise",
    CardanoAddressType.ENTERPRISE_SCRIPT: "Enterprise",
    CardanoAddressType.REWARD: "Reward",
    CardanoAddressType.REWARD_SCRIPT: "Reward",
}

SCRIPT_TYPE_NAMES = {
    CardanoNativeScriptType.PUB_KEY: "Key",
    CardanoNativeScriptType.ALL: "All",
    CardanoNativeScriptType.ANY: "Any",
    CardanoNativeScriptType.N_OF_K: "N of K",
    CardanoNativeScriptType.INVALID_BEFORE: "Invalid before",
    CardanoNativeScriptType.INVALID_HEREAFTER: "Invalid hereafter",
}

CERTIFICATE_TYPE_NAMES = {
    CardanoCertificateType.STAKE_REGISTRATION: "Stake key registration",
    CardanoCertificateType.STAKE_DEREGISTRATION: "Stake key deregistration",
    CardanoCertificateType.STAKE_DELEGATION: "Stake delegation",
    CardanoCertificateType.STAKE_POOL_REGISTRATION: "Stakepool registration",
}


def format_coin_amount(amount: int, network_id: int) -> str:
    currency = "ADA" if network_ids.is_mainnet(network_id) else "tADA"
    return f"{format_amount(amount, 6)} {currency}"


def is_printable_ascii_bytestring(bytestr: bytes) -> bool:
    return all((32 < b < 127) for b in bytestr)


async def show_native_script(
    ctx: wire.Context,
    script: CardanoNativeScript,
    indices: list[int] | None = None,
) -> None:
    script_heading = "Script"
    if indices is None:
        indices = []
    if indices:
        script_heading += " " + ".".join(str(i) for i in indices)

    script_type_name_suffix = ""
    if script.type == CardanoNativeScriptType.PUB_KEY:
        if script.key_path:
            script_type_name_suffix = "path"
        elif script.key_hash:
            script_type_name_suffix = "hash"

    props: list[PropertyType] = [
        (
            f"{script_heading} - {SCRIPT_TYPE_NAMES[script.type]} {script_type_name_suffix}:",
            None,
        )
    ]

    if script.type == CardanoNativeScriptType.PUB_KEY:
        assert script.key_hash is not None or script.key_path  # validate_script
        if script.key_hash:
            props.append(
                (None, bech32.encode(bech32.HRP_SHARED_KEY_HASH, script.key_hash))
            )
        elif script.key_path:
            props.append((address_n_to_str(script.key_path), None))
    elif script.type == CardanoNativeScriptType.N_OF_K:
        assert script.required_signatures_count is not None  # validate_script
        props.append(
            (
                f"Requires {script.required_signatures_count} out of {len(script.scripts)} signatures.",
                None,
            )
        )
    elif script.type == CardanoNativeScriptType.INVALID_BEFORE:
        assert script.invalid_before is not None  # validate_script
        props.append((str(script.invalid_before), None))
    elif script.type == CardanoNativeScriptType.INVALID_HEREAFTER:
        assert script.invalid_hereafter is not None  # validate_script
        props.append((str(script.invalid_hereafter), None))

    if script.type in (
        CardanoNativeScriptType.ALL,
        CardanoNativeScriptType.ANY,
        CardanoNativeScriptType.N_OF_K,
    ):
        assert script.scripts  # validate_script
        props.append((f"Contains {len(script.scripts)} nested scripts.", None))

    await confirm_properties(
        ctx,
        "verify_script",
        title="Verify script",
        props=props,
        br_code=ButtonRequestType.Other,
    )

    for i, sub_script in enumerate(script.scripts):
        await show_native_script(ctx, sub_script, indices + [i + 1])


async def show_script_hash(
    ctx: wire.Context,
    script_hash: bytes,
    display_format: CardanoNativeScriptHashDisplayFormat,
) -> None:
    assert display_format in (
        CardanoNativeScriptHashDisplayFormat.BECH32,
        CardanoNativeScriptHashDisplayFormat.POLICY_ID,
    )

    if display_format == CardanoNativeScriptHashDisplayFormat.BECH32:
        await confirm_properties(
            ctx,
            "verify_script",
            title="Verify script",
            props=[
                ("Script hash:", bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash))
            ],
            br_code=ButtonRequestType.Other,
        )
    elif display_format == CardanoNativeScriptHashDisplayFormat.POLICY_ID:
        await confirm_blob(
            ctx,
            "verify_script",
            title="Verify script",
            data=script_hash,
            description="Policy ID:",
            br_code=ButtonRequestType.Other,
        )


async def show_transaction_signing_mode(
    ctx: wire.Context, signing_mode: CardanoTxSigningMode
) -> None:
    if signing_mode == CardanoTxSigningMode.MULTISIG_TRANSACTION:
        await confirm_metadata(
            ctx,
            "confirm_signing_mode",
            title="Confirm transaction",
            content="Confirming a multisig transaction.",
            larger_vspace=True,
            br_code=ButtonRequestType.Other,
        )
    elif signing_mode == CardanoTxSigningMode.PLUTUS_TRANSACTION:
        await confirm_metadata(
            ctx,
            "confirm_signing_mode",
            title="Confirm transaction",
            content="Confirming a Plutus transaction - loss of collateral is possible. Check all items carefully.",
            br_code=ButtonRequestType.Other,
        )


async def confirm_input(ctx: wire.Context, input: CardanoTxInput) -> None:
    await confirm_properties(
        ctx,
        "confirm_input",
        title="Confirm transaction",
        props=[
            ("Input ID:", input.prev_hash),
            ("Input index:", str(input.prev_index)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_sending(
    ctx: wire.Context,
    ada_amount: int,
    to: str,
    is_change_output: bool,
    network_id: int,
) -> None:
    subtitle = "Change amount:" if is_change_output else "Confirm sending:"
    await confirm_output(
        ctx,
        to,
        format_coin_amount(ada_amount, network_id),
        title="Confirm transaction",
        subtitle=subtitle,
        font_amount=ui.BOLD,
        width_paginated=17,
        to_str="\nto\n",
        to_paginated=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_sending_token(
    ctx: wire.Context, policy_id: bytes, token: CardanoToken
) -> None:
    assert token.amount is not None  # _validate_token

    await confirm_properties(
        ctx,
        "confirm_token",
        title="Confirm transaction",
        props=[
            (
                "Asset fingerprint:",
                format_asset_fingerprint(
                    policy_id=policy_id,
                    asset_name_bytes=token.asset_name_bytes,
                ),
            ),
            ("Amount sent:", format_amount(token.amount, 0)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_address_credentials(
    ctx: wire.Context,
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = "Address"
    await _show_credential(ctx, payment_credential, intro_text, is_output=False)
    await _show_credential(ctx, stake_credential, intro_text, is_output=False)


async def show_change_output_credentials(
    ctx: wire.Context,
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = "The following address is a change address. Its"
    await _show_credential(ctx, payment_credential, intro_text, is_output=True)
    await _show_credential(ctx, stake_credential, intro_text, is_output=True)


async def show_device_owned_output_credentials(
    ctx: wire.Context,
    payment_credential: Credential,
    stake_credential: Credential,
    show_both_credentials: bool,
) -> None:
    intro_text = "The following address is owned by this device. Its"
    await _show_credential(ctx, payment_credential, intro_text, is_output=True)
    if show_both_credentials:
        await _show_credential(ctx, stake_credential, intro_text, is_output=True)


async def _show_credential(
    ctx: wire.Context,
    credential: Credential,
    intro_text: str,
    is_output: bool,
) -> None:
    if is_output:
        title = "Confirm transaction"
    else:
        title = f"{ADDRESS_TYPE_NAMES[credential.address_type]} address"

    props: list[PropertyType] = []

    # Credential can be empty in case of enterprise address stake credential
    # and reward address payment credential. In that case we don't want to
    # show some of the "props".
    if credential.is_set():
        credential_title = credential.get_title()
        props.append(
            (
                f"{intro_text} {credential.type_name} credential is a {credential_title}:",
                None,
            )
        )
        props.extend(credential.format())

    if credential.is_unusual_path:
        props.append((None, "Path is unusual."))
    if credential.is_mismatch:
        props.append((None, "Credential doesn't match payment credential."))
    if credential.is_reward:
        props.append(("Address is a reward address.", None))
    if credential.is_no_staking:
        props.append(
            (
                f"{ADDRESS_TYPE_NAMES[credential.address_type]} address - no staking rewards.",
                None,
            )
        )

    if credential.should_warn():
        icon = ui.ICON_WRONG
        icon_color = ui.RED
    else:
        icon = ui.ICON_SEND
        icon_color = ui.GREEN

    await confirm_properties(
        ctx,
        "confirm_credential",
        title=title,
        props=props,
        icon=icon,
        icon_color=icon_color,
        br_code=ButtonRequestType.Other,
    )


async def show_warning_path(ctx: wire.Context, path: list[int], title: str) -> None:
    await confirm_path_warning(ctx, address_n_to_str(path), path_type=title)


async def show_warning_tx_output_contains_tokens(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_tokens",
        title="Confirm transaction",
        content="The following\ntransaction output\ncontains tokens.",
        larger_vspace=True,
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_contains_mint(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_tokens",
        title="Confirm transaction",
        content="The transaction contains minting or burning of tokens.",
        larger_vspace=True,
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_output_contains_datum_hash(
    ctx: wire.Context, datum_hash: bytes
) -> None:
    await confirm_properties(
        ctx,
        "confirm_datum_hash",
        title="Confirm transaction",
        props=[
            (
                "The following transaction output contains datum hash:",
                bech32.encode(bech32.HRP_OUTPUT_DATUM_HASH, datum_hash),
            ),
            ("\nContinue?", None),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_output_no_datum_hash(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_no_datum_hash",
        title="Confirm transaction",
        content="The following transaction output contains a script address, but does not contain a datum hash.",
        br_code=ButtonRequestType.Other,
    )


async def show_warning_no_script_data_hash(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_no_script_data_hash",
        title="Confirm transaction",
        content="The transaction contains no script data hash. Plutus script will not be able to run.",
        br_code=ButtonRequestType.Other,
    )


async def show_warning_no_collateral_inputs(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_no_collateral_inputs",
        title="Confirm transaction",
        content="The transaction contains no collateral inputs. Plutus script will not be able to run.",
        br_code=ButtonRequestType.Other,
    )


async def confirm_witness_request(
    ctx: wire.Context,
    witness_path: list[int],
) -> None:
    if is_multisig_path(witness_path):
        path_title = "multi-sig path"
    elif is_minting_path(witness_path):
        path_title = "token minting path"
    else:
        path_title = "path"

    await confirm_text(
        ctx,
        "confirm_total",
        title="Confirm transaction",
        data=address_n_to_str(witness_path),
        description=f"Sign transaction with {path_title}:",
        br_code=ButtonRequestType.Other,
    )


async def confirm_transaction(
    ctx: wire.Context,
    fee: int,
    network_id: int,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
    is_network_id_verifiable: bool,
    tx_hash: bytes | None,
) -> None:
    props: list[PropertyType] = [
        ("Transaction fee:", format_coin_amount(fee, network_id)),
    ]

    if is_network_id_verifiable:
        props.append((f"Network: {protocol_magics.to_ui_string(protocol_magic)}", None))

    props.append((f"Valid since: {format_optional_int(validity_interval_start)}", None))
    props.append((f"TTL: {format_optional_int(ttl)}", None))

    if tx_hash:
        props.append(("Transaction ID:", tx_hash))

    await confirm_properties(
        ctx,
        "confirm_total",
        title="Confirm transaction",
        props=props,
        hold=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificate
) -> None:
    # stake pool registration requires custom confirmation logic not covered
    # in this call
    assert certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION

    props: list[PropertyType] = [
        ("Confirm:", CERTIFICATE_TYPE_NAMES[certificate.type]),
        _format_stake_credential(
            certificate.path, certificate.script_hash, certificate.key_hash
        ),
    ]

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        assert certificate.pool is not None  # validate_certificate
        props.append(("to pool:", format_stake_pool_id(certificate.pool)))

    await confirm_properties(
        ctx,
        "confirm_certificate",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_parameters(
    ctx: wire.Context, pool_parameters: CardanoPoolParametersType, network_id: int
) -> None:
    margin_percentage = (
        100.0 * pool_parameters.margin_numerator / pool_parameters.margin_denominator
    )
    percentage_formatted = str(float(margin_percentage)).rstrip("0").rstrip(".")
    await confirm_properties(
        ctx,
        "confirm_pool_registration",
        title="Confirm transaction",
        props=[
            (
                "Stake pool registration\nPool ID:",
                format_stake_pool_id(pool_parameters.pool_id),
            ),
            ("Pool reward account:", pool_parameters.reward_account),
            (
                f"Pledge: {format_coin_amount(pool_parameters.pledge, network_id)}\n"
                + f"Cost: {format_coin_amount(pool_parameters.cost, network_id)}\n"
                + f"Margin: {percentage_formatted}%",
                None,
            ),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_owner(
    ctx: wire.Context,
    keychain: seed.Keychain,
    owner: CardanoPoolOwner,
    protocol_magic: int,
    network_id: int,
) -> None:
    props: list[tuple[str, str | None]] = []
    if owner.staking_key_path:
        props.append(("Pool owner:", address_n_to_str(owner.staking_key_path)))
        props.append(
            (
                derive_human_readable_address(
                    keychain,
                    CardanoAddressParametersType(
                        address_type=CardanoAddressType.REWARD,
                        address_n=owner.staking_key_path,
                    ),
                    protocol_magic,
                    network_id,
                ),
                None,
            )
        )
    else:
        assert owner.staking_key_hash is not None  # validate_pool_owners
        props.append(
            (
                "Pool owner:",
                derive_human_readable_address(
                    keychain,
                    CardanoAddressParametersType(
                        address_type=CardanoAddressType.REWARD,
                        staking_key_hash=owner.staking_key_hash,
                    ),
                    protocol_magic,
                    network_id,
                ),
            )
        )

    await confirm_properties(
        ctx,
        "confirm_pool_owners",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_metadata(
    ctx: wire.Context,
    metadata: CardanoPoolMetadataType | None,
) -> None:
    if metadata is None:
        await confirm_properties(
            ctx,
            "confirm_pool_metadata",
            title="Confirm transaction",
            props=[("Pool has no metadata (anonymous pool)", None)],
            br_code=ButtonRequestType.Other,
        )
        return

    await confirm_properties(
        ctx,
        "confirm_pool_metadata",
        title="Confirm transaction",
        props=[
            ("Pool metadata url:", metadata.url),
            ("Pool metadata hash:", metadata.hash),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_registration_final(
    ctx: wire.Context,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
) -> None:
    await confirm_properties(
        ctx,
        "confirm_pool_final",
        title="Confirm transaction",
        props=[
            ("Confirm signing the stake pool registration as an owner.", None),
            ("Network:", protocol_magics.to_ui_string(protocol_magic)),
            ("Valid since:", format_optional_int(validity_interval_start)),
            ("TTL:", format_optional_int(ttl)),
        ],
        hold=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_withdrawal(
    ctx: wire.Context,
    withdrawal: CardanoTxWithdrawal,
    reward_address_bytes: bytes,
    network_id: int,
) -> None:
    address_type_name = "script reward" if withdrawal.script_hash else "reward"
    reward_address = encode_human_readable_address(reward_address_bytes)
    props: list[PropertyType] = [
        (f"Confirm withdrawal for {address_type_name} address:", reward_address),
    ]

    if withdrawal.path:
        props.append(
            _format_stake_credential(
                withdrawal.path, withdrawal.script_hash, withdrawal.key_hash
            )
        )

    props.append(("Amount:", format_coin_amount(withdrawal.amount, network_id)))

    await confirm_properties(
        ctx,
        "confirm_withdrawal",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


def _format_stake_credential(
    path: list[int], script_hash: bytes | None, key_hash: bytes | None
) -> tuple[str, str]:
    if path:
        return (
            f"for account {format_account_number(path)}:",
            address_n_to_str(to_account_path(path)),
        )
    elif key_hash:
        return ("for key hash:", bech32.encode(bech32.HRP_STAKE_KEY_HASH, key_hash))
    elif script_hash:
        return ("for script:", bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash))
    else:
        # should be unreachable unless there's a bug in validation
        raise ValueError


async def confirm_catalyst_registration(
    ctx: wire.Context,
    public_key: str,
    staking_path: list[int],
    reward_address: str,
    nonce: int,
) -> None:
    await confirm_properties(
        ctx,
        "confirm_catalyst_registration",
        title="Confirm transaction",
        props=[
            ("Catalyst voting key registration", None),
            ("Voting public key:", public_key),
            (
                f"Staking key for account {format_account_number(staking_path)}:",
                address_n_to_str(staking_path),
            ),
            ("Rewards go to:", reward_address),
            ("Nonce:", str(nonce)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_auxiliary_data_hash(
    ctx: wire.Context, auxiliary_data_hash: bytes
) -> None:
    await confirm_properties(
        ctx,
        "confirm_auxiliary_data",
        title="Confirm transaction",
        props=[("Auxiliary data hash:", auxiliary_data_hash)],
        br_code=ButtonRequestType.Other,
    )


async def confirm_token_minting(
    ctx: wire.Context, policy_id: bytes, token: CardanoToken
) -> None:
    assert token.mint_amount is not None  # _validate_token
    await confirm_properties(
        ctx,
        "confirm_mint",
        title="Confirm transaction",
        props=[
            (
                "Asset fingerprint:",
                format_asset_fingerprint(
                    policy_id=policy_id,
                    asset_name_bytes=token.asset_name_bytes,
                ),
            ),
            (
                "Amount minted:" if token.mint_amount >= 0 else "Amount burned:",
                format_amount(token.mint_amount, 0),
            ),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_network_unverifiable(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "warning_no_outputs",
        title="Warning",
        content="Transaction has no outputs, network cannot be verified.",
        larger_vspace=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_script_data_hash(ctx: wire.Context, script_data_hash: bytes) -> None:
    await confirm_properties(
        ctx,
        "confirm_script_data_hash",
        title="Confirm transaction",
        props=[
            (
                "Script data hash:",
                bech32.encode(bech32.HRP_SCRIPT_DATA_HASH, script_data_hash),
            )
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_collateral_input(
    ctx: wire.Context, collateral_input: CardanoTxCollateralInput
) -> None:
    await confirm_properties(
        ctx,
        "confirm_collateral_input",
        title="Confirm transaction",
        props=[
            ("Collateral input ID:", collateral_input.prev_hash),
            ("Collateral input index:", str(collateral_input.prev_index)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_required_signer(
    ctx: wire.Context, required_signer: CardanoTxRequiredSigner
) -> None:
    assert (
        required_signer.key_hash is not None or required_signer.key_path
    )  # _validate_required_signer
    formatted_signer = (
        bech32.encode(bech32.HRP_REQUIRED_SIGNER_KEY_HASH, required_signer.key_hash)
        if required_signer.key_hash is not None
        else address_n_to_str(required_signer.key_path)
    )

    await confirm_properties(
        ctx,
        "confirm_required_signer",
        title="Confirm transaction",
        props=[("Required signer", formatted_signer)],
        br_code=ButtonRequestType.Other,
    )


async def show_cardano_address(
    ctx: wire.Context,
    address_parameters: CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
) -> None:
    network_name = None
    if not protocol_magics.is_mainnet(protocol_magic):
        network_name = protocol_magics.to_ui_string(protocol_magic)

    title = f"{ADDRESS_TYPE_NAMES[address_parameters.address_type]} address"
    address_extra = None
    title_qr = title
    if address_parameters.address_type in (
        CardanoAddressType.BYRON,
        CardanoAddressType.BASE,
        CardanoAddressType.BASE_KEY_SCRIPT,
        CardanoAddressType.POINTER,
        CardanoAddressType.ENTERPRISE,
        CardanoAddressType.REWARD,
    ):
        if address_parameters.address_n:
            address_extra = address_n_to_str(address_parameters.address_n)
            title_qr = address_n_to_str(address_parameters.address_n)
        elif address_parameters.address_n_staking:
            address_extra = address_n_to_str(address_parameters.address_n_staking)
            title_qr = address_n_to_str(address_parameters.address_n_staking)

    await show_address(
        ctx,
        address=address,
        title=title,
        network=network_name,
        address_extra=address_extra,
        title_qr=title_qr,
    )
