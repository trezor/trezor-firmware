from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
    CardanoNativeScriptType,
)
from trezor.strings import format_amount
from trezor.ui import layouts
from trezor.ui.layouts import confirm_metadata, confirm_properties

from apps.common.paths import address_n_to_str

from . import addresses
from .helpers import bech32, protocol_magics
from .helpers.utils import (
    format_account_number,
    format_asset_fingerprint,
    format_optional_int,
    format_stake_pool_id,
)

if TYPE_CHECKING:
    from typing import Literal

    from trezor import messages
    from trezor.enums import CardanoNativeScriptHashDisplayFormat
    from trezor.ui.layouts import PropertyType

    from .helpers.credential import Credential
    from .seed import Keychain


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

BRT_Other = ButtonRequestType.Other  # global_import_cache

CVOTE_REWARD_ELIGIBILITY_WARNING = (
    "Warning: The address is not a payment address, it is not eligible for rewards."
)


def format_coin_amount(amount: int, network_id: int) -> str:
    from .helpers import network_ids

    currency = "ADA" if network_ids.is_mainnet(network_id) else "tADA"
    return f"{format_amount(amount, 6)} {currency}"


async def show_native_script(
    script: messages.CardanoNativeScript,
    indices: list[int] | None = None,
) -> None:
    CNST = CardanoNativeScriptType  # local_cache_global
    script_type = script.type  # local_cache_attribute
    key_path = script.key_path  # local_cache_attribute
    key_hash = script.key_hash  # local_cache_attribute
    scripts = script.scripts  # local_cache_attribute

    script_heading = "Script"
    if indices is None:
        indices = []
    if indices:
        script_heading += " " + ".".join(str(i) for i in indices)

    script_type_name_suffix = ""
    if script_type == CNST.PUB_KEY:
        if key_path:
            script_type_name_suffix = "path"
        elif key_hash:
            script_type_name_suffix = "hash"

    props: list[PropertyType] = [
        (
            f"{script_heading} - {SCRIPT_TYPE_NAMES[script_type]} {script_type_name_suffix}:",
            None,
        )
    ]
    append = props.append  # local_cache_attribute

    if script_type == CNST.PUB_KEY:
        assert key_hash is not None or key_path  # validate_script
        if key_hash:
            append((None, bech32.encode(bech32.HRP_SHARED_KEY_HASH, key_hash)))
        elif key_path:
            append((address_n_to_str(key_path), None))
    elif script_type == CNST.N_OF_K:
        assert script.required_signatures_count is not None  # validate_script
        append(
            (
                f"Requires {script.required_signatures_count} out of {len(scripts)} signatures.",
                None,
            )
        )
    elif script_type == CNST.INVALID_BEFORE:
        assert script.invalid_before is not None  # validate_script
        append((str(script.invalid_before), None))
    elif script_type == CNST.INVALID_HEREAFTER:
        assert script.invalid_hereafter is not None  # validate_script
        append((str(script.invalid_hereafter), None))

    if script_type in (
        CNST.ALL,
        CNST.ANY,
        CNST.N_OF_K,
    ):
        assert scripts  # validate_script
        append((f"Contains {len(scripts)} nested scripts.", None))

    await confirm_properties(
        "verify_script",
        "Verify script",
        props,
        br_code=BRT_Other,
    )

    for i, sub_script in enumerate(scripts):
        await show_native_script(sub_script, indices + [i + 1])


async def show_script_hash(
    script_hash: bytes,
    display_format: CardanoNativeScriptHashDisplayFormat,
) -> None:
    from trezor.enums import CardanoNativeScriptHashDisplayFormat

    assert display_format in (
        CardanoNativeScriptHashDisplayFormat.BECH32,
        CardanoNativeScriptHashDisplayFormat.POLICY_ID,
    )

    if display_format == CardanoNativeScriptHashDisplayFormat.BECH32:
        await confirm_properties(
            "verify_script",
            "Verify script",
            (("Script hash:", bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash)),),
            br_code=BRT_Other,
        )
    elif display_format == CardanoNativeScriptHashDisplayFormat.POLICY_ID:
        await layouts.confirm_blob(
            "verify_script",
            "Verify script",
            script_hash,
            "Policy ID:",
            br_code=BRT_Other,
        )


async def show_tx_init(title: str) -> bool:
    should_show_details = await layouts.should_show_more(
        "Confirm transaction",
        (
            (
                ui.DEMIBOLD,
                title,
            ),
            (ui.NORMAL, "Choose level of details:"),
        ),
        "Show All",
        confirm="Show Simple",
    )

    return should_show_details


async def confirm_input(input: messages.CardanoTxInput) -> None:
    await confirm_properties(
        "confirm_input",
        "Confirm transaction",
        (
            ("Input ID:", input.prev_hash),
            ("Input index:", str(input.prev_index)),
        ),
        br_code=BRT_Other,
    )


async def confirm_sending(
    ada_amount: int,
    to: str,
    output_type: Literal["address", "change", "collateral-return"],
    network_id: int,
) -> None:
    if output_type == "address":
        title = "Sending"
    elif output_type == "change":
        title = "Change output"
    elif output_type == "collateral-return":
        title = "Collateral return"
    else:
        raise RuntimeError  # should be unreachable

    await layouts.confirm_output(
        to,
        format_coin_amount(ada_amount, network_id),
        title,
        br_code=ButtonRequestType.Other,
    )


async def confirm_sending_token(policy_id: bytes, token: messages.CardanoToken) -> None:
    assert token.amount is not None  # _validate_token

    await confirm_properties(
        "confirm_token",
        "Confirm transaction",
        (
            (
                "Asset fingerprint:",
                format_asset_fingerprint(
                    policy_id=policy_id,
                    asset_name_bytes=token.asset_name_bytes,
                ),
            ),
            ("Amount sent:", format_amount(token.amount, 0)),
        ),
        br_code=BRT_Other,
    )


async def confirm_datum_hash(datum_hash: bytes) -> None:
    await confirm_properties(
        "confirm_datum_hash",
        "Confirm transaction",
        (
            (
                "Datum hash:",
                bech32.encode(bech32.HRP_OUTPUT_DATUM_HASH, datum_hash),
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_inline_datum(first_chunk: bytes, inline_datum_size: int) -> None:
    await _confirm_data_chunk(
        "confirm_inline_datum",
        "Inline datum",
        first_chunk,
        inline_datum_size,
    )


async def confirm_reference_script(
    first_chunk: bytes, reference_script_size: int
) -> None:
    await _confirm_data_chunk(
        "confirm_reference_script",
        "Reference script",
        first_chunk,
        reference_script_size,
    )


async def _confirm_data_chunk(
    br_type: str, title: str, first_chunk: bytes, data_size: int
) -> None:
    MAX_DISPLAYED_SIZE = 56
    displayed_bytes = first_chunk[:MAX_DISPLAYED_SIZE]
    bytes_optional_plural = "byte" if data_size == 1 else "bytes"
    props: list[tuple[str, bytes | None]] = [
        (
            f"{title} ({data_size} {bytes_optional_plural}):",
            displayed_bytes,
        )
    ]
    if data_size > MAX_DISPLAYED_SIZE:
        props.append(("...", None))
    await confirm_properties(
        br_type,
        title="Confirm transaction",
        props=props,
        br_code=BRT_Other,
    )


async def show_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = "Address"
    await _show_credential(payment_credential, intro_text, purpose="address")
    await _show_credential(stake_credential, intro_text, purpose="address")


async def show_change_output_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = "The following address is a change address. Its"
    await _show_credential(payment_credential, intro_text, purpose="output")
    await _show_credential(stake_credential, intro_text, purpose="output")


async def show_device_owned_output_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
    show_both_credentials: bool,
) -> None:
    intro_text = "The following address is owned by this device. Its"
    await _show_credential(payment_credential, intro_text, purpose="output")
    if show_both_credentials:
        await _show_credential(stake_credential, intro_text, purpose="output")


async def show_cvote_registration_payment_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
    show_both_credentials: bool,
    show_payment_warning: bool,
) -> None:
    intro_text = (
        "The vote key registration payment address is owned by this device. Its"
    )
    await _show_credential(
        payment_credential, intro_text, purpose="cvote_reg_payment_address"
    )
    if show_both_credentials or show_payment_warning:
        extra_text = CVOTE_REWARD_ELIGIBILITY_WARNING if show_payment_warning else None
        await _show_credential(
            stake_credential,
            intro_text,
            purpose="cvote_reg_payment_address",
            extra_text=extra_text,
        )


async def _show_credential(
    credential: Credential,
    intro_text: str,
    purpose: Literal["address", "output", "cvote_reg_payment_address"],
    extra_text: str | None = None,
) -> None:
    title = {
        "address": f"{ADDRESS_TYPE_NAMES[credential.address_type]} address",
        "output": "Confirm transaction",
        "cvote_reg_payment_address": "Confirm transaction",
    }[purpose]

    props: list[PropertyType] = []
    append = props.append  # local_cache_attribute

    # Credential can be empty in case of enterprise address stake credential
    # and reward address payment credential. In that case we don't want to
    # show some of the "props".
    if credential.is_set():
        credential_title = credential.get_title()
        append(
            (
                f"{intro_text} {credential.type_name} credential is a {credential_title}:",
                None,
            )
        )
        props.extend(credential.format())

    if credential.is_unusual_path:
        append((None, "Path is unusual."))
    if credential.is_mismatch:
        append((None, "Credential doesn't match payment credential."))
    if credential.is_reward and purpose != "cvote_reg_payment_address":
        # for cvote registrations, this is handled by extra_text at the end
        append(("Address is a reward address.", None))
    if credential.is_no_staking:
        append(
            (
                f"{ADDRESS_TYPE_NAMES[credential.address_type]} address - no staking rewards.",
                None,
            )
        )

    if extra_text:
        append((extra_text, None))

    if len(props) > 0:
        await confirm_properties(
            "confirm_credential",
            title,
            props,
            br_code=BRT_Other,
        )


async def warn_path(path: list[int], title: str) -> None:
    await layouts.confirm_path_warning(address_n_to_str(path), path_type=title)


async def warn_tx_output_contains_tokens(is_collateral_return: bool = False) -> None:
    content = (
        "The collateral return output contains tokens."
        if is_collateral_return
        else "The following transaction output contains tokens."
    )
    await confirm_metadata(
        "confirm_tokens",
        "Confirm transaction",
        content,
        br_code=BRT_Other,
    )


async def warn_tx_contains_mint() -> None:
    await confirm_metadata(
        "confirm_tokens",
        "Confirm transaction",
        "The transaction contains minting or burning of tokens.",
        br_code=BRT_Other,
    )


async def warn_tx_output_no_datum() -> None:
    await confirm_metadata(
        "confirm_no_datum_hash",
        "Confirm transaction",
        "The following transaction output contains a script address, but does not contain a datum.",
        br_code=BRT_Other,
    )


async def warn_no_script_data_hash() -> None:
    await confirm_metadata(
        "confirm_no_script_data_hash",
        "Confirm transaction",
        "The transaction contains no script data hash. Plutus script will not be able to run.",
        br_code=BRT_Other,
    )


async def warn_no_collateral_inputs() -> None:
    await confirm_metadata(
        "confirm_no_collateral_inputs",
        "Confirm transaction",
        "The transaction contains no collateral inputs. Plutus script will not be able to run.",
        br_code=BRT_Other,
    )


async def warn_unknown_total_collateral() -> None:
    await layouts.show_warning(
        "confirm_unknown_total_collateral",
        "Unknown collateral amount.",
        "Check all items carefully.",
        br_code=BRT_Other,
    )


async def confirm_witness_request(
    witness_path: list[int],
) -> None:
    from . import seed

    if seed.is_multisig_path(witness_path):
        path_title = "multi-sig path"
    elif seed.is_minting_path(witness_path):
        path_title = "token minting path"
    else:
        path_title = "path"

    await layouts.confirm_text(
        "confirm_total",
        "Confirm transaction",
        address_n_to_str(witness_path),
        f"Sign transaction with {path_title}:",
        BRT_Other,
    )


async def confirm_tx(
    fee: int,
    network_id: int,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
    total_collateral: int | None,
    is_network_id_verifiable: bool,
    tx_hash: bytes | None,
) -> None:
    props: list[PropertyType] = [
        ("Transaction fee:", format_coin_amount(fee, network_id)),
    ]
    append = props.append  # local_cache_attribute

    if total_collateral is not None:
        append(("Total collateral:", format_coin_amount(total_collateral, network_id)))

    if is_network_id_verifiable:
        append((f"Network: {protocol_magics.to_ui_string(protocol_magic)}", None))

    append((f"Valid since: {format_optional_int(validity_interval_start)}", None))
    append((f"TTL: {format_optional_int(ttl)}", None))

    if tx_hash:
        append(("Transaction ID:", tx_hash))

    await confirm_properties(
        "confirm_total",
        "Confirm transaction",
        props,
        hold=True,
        br_code=BRT_Other,
    )


async def confirm_certificate(certificate: messages.CardanoTxCertificate) -> None:
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
        "confirm_certificate",
        "Confirm transaction",
        props,
        br_code=BRT_Other,
    )


async def confirm_stake_pool_parameters(
    pool_parameters: messages.CardanoPoolParametersType,
    network_id: int,
) -> None:
    margin_percentage = (
        100.0 * pool_parameters.margin_numerator / pool_parameters.margin_denominator
    )
    percentage_formatted = str(float(margin_percentage)).rstrip("0").rstrip(".")
    await confirm_properties(
        "confirm_pool_registration",
        "Confirm transaction",
        (
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
        ),
        br_code=BRT_Other,
    )


async def confirm_stake_pool_owner(
    keychain: Keychain,
    owner: messages.CardanoPoolOwner,
    protocol_magic: int,
    network_id: int,
) -> None:
    from trezor import messages

    props: list[tuple[str, str | None]] = []
    if owner.staking_key_path:
        props.append(("Pool owner:", address_n_to_str(owner.staking_key_path)))
        props.append(
            (
                addresses.derive_human_readable(
                    keychain,
                    messages.CardanoAddressParametersType(
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
                addresses.derive_human_readable(
                    keychain,
                    messages.CardanoAddressParametersType(
                        address_type=CardanoAddressType.REWARD,
                        staking_key_hash=owner.staking_key_hash,
                    ),
                    protocol_magic,
                    network_id,
                ),
            )
        )

    await confirm_properties(
        "confirm_pool_owners",
        "Confirm transaction",
        props,
        br_code=BRT_Other,
    )


async def confirm_stake_pool_metadata(
    metadata: messages.CardanoPoolMetadataType | None,
) -> None:
    if metadata is None:
        await confirm_properties(
            "confirm_pool_metadata",
            "Confirm transaction",
            (("Pool has no metadata (anonymous pool)", None),),
            br_code=BRT_Other,
        )
        return

    await confirm_properties(
        "confirm_pool_metadata",
        "Confirm transaction",
        (
            ("Pool metadata url:", metadata.url),
            ("Pool metadata hash:", metadata.hash),
        ),
        br_code=BRT_Other,
    )


async def confirm_stake_pool_registration_final(
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
) -> None:
    await confirm_properties(
        "confirm_pool_final",
        "Confirm transaction",
        (
            ("Confirm signing the stake pool registration as an owner.", None),
            ("Network:", protocol_magics.to_ui_string(protocol_magic)),
            ("Valid since:", format_optional_int(validity_interval_start)),
            ("TTL:", format_optional_int(ttl)),
        ),
        hold=True,
        br_code=BRT_Other,
    )


async def confirm_withdrawal(
    withdrawal: messages.CardanoTxWithdrawal,
    address_bytes: bytes,
    network_id: int,
) -> None:
    address_type_name = "script reward" if withdrawal.script_hash else "reward"
    address = addresses.encode_human_readable(address_bytes)
    props: list[PropertyType] = [
        (f"Confirm withdrawal for {address_type_name} address:", address),
    ]

    if withdrawal.path:
        props.append(
            _format_stake_credential(
                withdrawal.path, withdrawal.script_hash, withdrawal.key_hash
            )
        )

    props.append(("Amount:", format_coin_amount(withdrawal.amount, network_id)))

    await confirm_properties(
        "confirm_withdrawal",
        "Confirm transaction",
        props,
        br_code=BRT_Other,
    )


def _format_stake_credential(
    path: list[int], script_hash: bytes | None, key_hash: bytes | None
) -> tuple[str, str]:
    from .helpers.utils import to_account_path

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


async def confirm_cvote_registration_delegation(
    public_key: str,
    weight: int,
) -> None:
    props: list[PropertyType] = [
        ("Vote key registration (CIP-36)", None),
        ("Delegating to:", public_key),
    ]
    if weight is not None:
        props.append(("Weight:", str(weight)))

    await confirm_properties(
        "confirm_cvote_registration_delegation",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_cvote_registration_payment_address(
    payment_address: str,
    should_show_payment_warning: bool,
) -> None:
    props = [
        ("Vote key registration (CIP-36)", None),
        ("Rewards go to:", payment_address),
    ]
    if should_show_payment_warning:
        props.append((CVOTE_REWARD_ELIGIBILITY_WARNING, None))
    await confirm_properties(
        "confirm_cvote_registration_payment_address",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_cvote_registration(
    vote_public_key: str | None,
    staking_path: list[int],
    nonce: int,
    voting_purpose: int | None,
) -> None:
    props: list[PropertyType] = [("Vote key registration (CIP-36)", None)]
    if vote_public_key is not None:
        props.append(("Vote public key:", vote_public_key))
    props.extend(
        [
            (
                f"Staking key for account {format_account_number(staking_path)}:",
                address_n_to_str(staking_path),
            ),
            ("Nonce:", str(nonce)),
        ]
    )
    if voting_purpose is not None:
        props.append(
            (
                "Voting purpose:",
                "Catalyst" if voting_purpose == 0 else f"{voting_purpose} (other)",
            )
        )

    await confirm_properties(
        "confirm_cvote_registration",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def show_auxiliary_data_hash(auxiliary_data_hash: bytes) -> None:
    await confirm_properties(
        "confirm_auxiliary_data",
        "Confirm transaction",
        (("Auxiliary data hash:", auxiliary_data_hash),),
        br_code=BRT_Other,
    )


async def confirm_token_minting(policy_id: bytes, token: messages.CardanoToken) -> None:
    assert token.mint_amount is not None  # _validate_token
    await confirm_properties(
        "confirm_mint",
        "Confirm transaction",
        (
            (
                "Asset fingerprint:",
                format_asset_fingerprint(
                    policy_id,
                    token.asset_name_bytes,
                ),
            ),
            (
                "Amount minted:" if token.mint_amount >= 0 else "Amount burned:",
                format_amount(token.mint_amount, 0),
            ),
        ),
        br_code=BRT_Other,
    )


async def warn_tx_network_unverifiable() -> None:
    await confirm_metadata(
        "warning_no_outputs",
        "Warning",
        "Transaction has no outputs, network cannot be verified.",
        br_code=BRT_Other,
    )


async def confirm_script_data_hash(script_data_hash: bytes) -> None:
    await confirm_properties(
        "confirm_script_data_hash",
        "Confirm transaction",
        (
            (
                "Script data hash:",
                bech32.encode(bech32.HRP_SCRIPT_DATA_HASH, script_data_hash),
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_collateral_input(
    collateral_input: messages.CardanoTxCollateralInput,
) -> None:
    await confirm_properties(
        "confirm_collateral_input",
        "Confirm transaction",
        (
            ("Collateral input ID:", collateral_input.prev_hash),
            ("Collateral input index:", str(collateral_input.prev_index)),
        ),
        br_code=BRT_Other,
    )


async def confirm_reference_input(
    reference_input: messages.CardanoTxReferenceInput,
) -> None:
    await confirm_properties(
        "confirm_reference_input",
        "Confirm transaction",
        (
            ("Reference input ID:", reference_input.prev_hash),
            ("Reference input index:", str(reference_input.prev_index)),
        ),
        br_code=BRT_Other,
    )


async def confirm_required_signer(
    required_signer: messages.CardanoTxRequiredSigner,
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
        "confirm_required_signer",
        "Confirm transaction",
        (("Required signer", formatted_signer),),
        br_code=BRT_Other,
    )


async def show_cardano_address(
    address_parameters: messages.CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
) -> None:
    CAT = CardanoAddressType  # local_cache_global

    network_name = None
    if not protocol_magics.is_mainnet(protocol_magic):
        network_name = protocol_magics.to_ui_string(protocol_magic)

    path = None
    account = ADDRESS_TYPE_NAMES[address_parameters.address_type]
    if address_parameters.address_type in (
        CAT.BYRON,
        CAT.BASE,
        CAT.BASE_KEY_SCRIPT,
        CAT.POINTER,
        CAT.ENTERPRISE,
        CAT.REWARD,
    ):
        if address_parameters.address_n:
            path = address_n_to_str(address_parameters.address_n)
        elif address_parameters.address_n_staking:
            path = address_n_to_str(address_parameters.address_n_staking)

    await layouts.show_address(
        address,
        path=path,
        account=account,
        network=network_name,
    )
