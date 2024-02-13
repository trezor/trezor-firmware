from typing import TYPE_CHECKING

from trezor import TR, wire
from trezor.enums import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
    CardanoDRepType,
    CardanoNativeScriptType,
)
from trezor.strings import format_amount, format_amount_unit
from trezor.ui import layouts
from trezor.ui.layouts import confirm_metadata, confirm_properties
from trezor.wire import ProcessError

from apps.cardano.helpers.chunks import MAX_CHUNK_SIZE
from apps.common.paths import address_n_to_str

from . import addresses
from .helpers import bech32, protocol_magics
from .helpers.utils import (
    format_account_number,
    format_asset_fingerprint,
    format_optional_int,
    format_stake_pool_id,
    is_unambiguous_ascii,
)

if TYPE_CHECKING:
    from typing import Callable, Literal

    from trezor import messages
    from trezor.enums import CardanoNativeScriptHashDisplayFormat
    from trezor.messages import PaymentRequest
    from trezor.ui.layouts import PropertyType

    from apps.common.paths import Bip32Path

    from .helpers.credential import Credential
    from .seed import Keychain


ADDRESS_TYPE_NAMES = {
    CardanoAddressType.BYRON: TR.cardano__addr_legacy,
    CardanoAddressType.BASE: TR.cardano__addr_base,
    CardanoAddressType.BASE_SCRIPT_KEY: TR.cardano__addr_base,
    CardanoAddressType.BASE_KEY_SCRIPT: TR.cardano__addr_base,
    CardanoAddressType.BASE_SCRIPT_SCRIPT: TR.cardano__addr_base,
    CardanoAddressType.POINTER: TR.cardano__addr_pointer,
    CardanoAddressType.POINTER_SCRIPT: TR.cardano__addr_pointer,
    CardanoAddressType.ENTERPRISE: TR.cardano__addr_enterprise,
    CardanoAddressType.ENTERPRISE_SCRIPT: TR.cardano__addr_enterprise,
    CardanoAddressType.REWARD: TR.cardano__addr_reward,
    CardanoAddressType.REWARD_SCRIPT: TR.cardano__addr_reward,
}

SCRIPT_TYPE_NAMES = {
    CardanoNativeScriptType.PUB_KEY: TR.cardano__script_key,
    CardanoNativeScriptType.ALL: TR.cardano__script_all,
    CardanoNativeScriptType.ANY: TR.cardano__script_any,
    CardanoNativeScriptType.N_OF_K: TR.cardano__script_n_of_k,
    CardanoNativeScriptType.INVALID_BEFORE: TR.cardano__script_invalid_before,
    CardanoNativeScriptType.INVALID_HEREAFTER: TR.cardano__script_invalid_hereafter,
}

CERTIFICATE_TYPE_NAMES = {
    CardanoCertificateType.STAKE_REGISTRATION: TR.cardano__stake_registration,
    CardanoCertificateType.STAKE_REGISTRATION_CONWAY: TR.cardano__stake_registration,
    CardanoCertificateType.STAKE_DEREGISTRATION: TR.cardano__stake_deregistration,
    CardanoCertificateType.STAKE_DEREGISTRATION_CONWAY: TR.cardano__stake_deregistration,
    CardanoCertificateType.STAKE_DELEGATION: TR.cardano__stake_delegation,
    CardanoCertificateType.STAKE_POOL_REGISTRATION: TR.cardano__stake_pool_registration,
    CardanoCertificateType.VOTE_DELEGATION: TR.cardano__vote_delegation,
}

BRT_Other = ButtonRequestType.Other  # global_import_cache

CVOTE_REWARD_ELIGIBILITY_WARNING = TR.cardano__reward_eligibility_warning

_DEFAULT_MAX_DISPLAYED_CHUNK_SIZE = 56


def format_coin_amount(amount: int, network_id: int) -> str:
    from .helpers import network_ids

    currency = "ADA" if network_ids.is_mainnet(network_id) else "tADA"
    return f"{format_amount_unit(format_amount(amount, 6), currency)}"


async def show_native_script(
    script: messages.CardanoNativeScript,
    indices: list[int] | None = None,
) -> None:
    CNST = CardanoNativeScriptType  # local_cache_global
    script_type = script.type  # local_cache_attribute
    key_path = script.key_path  # local_cache_attribute
    key_hash = script.key_hash  # local_cache_attribute
    scripts = script.scripts  # local_cache_attribute

    if indices is None:
        indices = []

    async def confirm_native_script() -> None:
        script_heading = "Script"
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
                None,
            )
        ]
        append = props.append  # local_cache_attribute

        if script_type == CNST.PUB_KEY:
            assert key_hash is not None or key_path  # validate_script
            if key_hash:
                append(
                    (None, bech32.encode(bech32.HRP_SHARED_KEY_HASH, key_hash), True)
                )
            elif key_path:
                append((address_n_to_str(key_path), None, None))
        elif script_type == CNST.N_OF_K:
            assert script.required_signatures_count is not None  # validate_script
            append(
                (
                    TR.cardano__x_of_y_signatures_template.format(
                        script.required_signatures_count, len(scripts)
                    ),
                    None,
                    None,
                )
            )
        elif script_type == CNST.INVALID_BEFORE:
            assert script.invalid_before is not None  # validate_script
            append((str(script.invalid_before), None, None))
        elif script_type == CNST.INVALID_HEREAFTER:
            assert script.invalid_hereafter is not None  # validate_script
            append((str(script.invalid_hereafter), None, None))

        if script_type in (
            CNST.ALL,
            CNST.ANY,
            CNST.N_OF_K,
        ):
            assert scripts  # validate_script
            append(
                (TR.cardano__nested_scripts_template.format(len(scripts)), None, None)
            )

        await confirm_properties(
            "verify_script",
            TR.cardano__verify_script,
            props,
            br_code=BRT_Other,
        )

    # Allow GC to free local variables after confirmation is over
    await confirm_native_script()

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
            TR.cardano__verify_script,
            (
                (
                    TR.cardano__script_hash,
                    bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash),
                    True,
                ),
            ),
            br_code=BRT_Other,
        )
    elif display_format == CardanoNativeScriptHashDisplayFormat.POLICY_ID:
        await layouts.confirm_blob(
            "verify_script",
            TR.cardano__verify_script,
            script_hash,
            TR.cardano__policy_id,
            br_code=BRT_Other,
        )


async def show_tx_init(title: str) -> bool:
    should_show_details = await layouts.should_show_more(
        TR.cardano__confirm_transaction,
        (
            (title, False),
            (TR.cardano__choose_level_of_details, False),
        ),
        TR.buttons__show_all,
        confirm=TR.cardano__show_simple,
    )

    return should_show_details


async def confirm_input(input: messages.CardanoTxInput) -> None:
    await confirm_properties(
        "confirm_input",
        TR.cardano__confirm_transaction,
        (
            (TR.cardano__input_id, input.prev_hash, True),
            (TR.cardano__input_index, str(input.prev_index), True),
        ),
        br_code=BRT_Other,
    )


async def confirm_sending(
    ada_amount: int,
    to: str,
    output_type: Literal["address", "change", "collateral-return"],
    output_index: int | None,
    network_id: int,
    chunkify: bool,
) -> None:
    output_index_shown = None
    if output_type == "address":
        if output_index is None:
            title = TR.cardano__sending
        else:
            title = None
            output_index_shown = output_index
    elif output_type == "change":
        title = TR.cardano__change_output
    elif output_type == "collateral-return":
        title = TR.cardano__collateral_return
    else:
        raise RuntimeError  # should be unreachable

    await layouts.confirm_output(
        to,
        format_coin_amount(ada_amount, network_id),
        title,
        br_code=ButtonRequestType.Other,
        chunkify=chunkify,
        output_index=output_index_shown,
    )


async def confirm_sending_token(policy_id: bytes, token: messages.CardanoToken) -> None:
    assert token.amount is not None  # _validate_token

    await confirm_properties(
        "confirm_token",
        TR.cardano__confirm_transaction,
        (
            (
                TR.cardano__asset_fingerprint,
                format_asset_fingerprint(
                    policy_id=policy_id,
                    asset_name_bytes=token.asset_name_bytes,
                ),
                True,
            ),
            (
                TR.cardano__amount_sent_decimals_unknown,
                format_amount(token.amount, 0),
                True,
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_datum_hash(datum_hash: bytes) -> None:
    await confirm_properties(
        "confirm_datum_hash",
        TR.cardano__confirm_transaction,
        (
            (
                TR.cardano__datum_hash,
                bech32.encode(bech32.HRP_OUTPUT_DATUM_HASH, datum_hash),
                True,
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_inline_datum(first_chunk: bytes, inline_datum_size: int) -> None:
    await _confirm_tx_data_chunk(
        "confirm_inline_datum",
        TR.cardano__inline_datum,
        first_chunk,
        inline_datum_size,
    )


async def confirm_reference_script(
    first_chunk: bytes, reference_script_size: int
) -> None:
    await _confirm_tx_data_chunk(
        "confirm_reference_script",
        TR.cardano__reference_script,
        first_chunk,
        reference_script_size,
    )


async def confirm_message_payload(
    payload_first_chunk: bytes,
    payload_hash: bytes,
    payload_size: int,
    is_signing_hash: bool,
    display_ascii: bool,
) -> None:
    props: list[PropertyType]

    max_displayed_bytes = (
        _DEFAULT_MAX_DISPLAYED_CHUNK_SIZE if is_signing_hash else MAX_CHUNK_SIZE
    )

    if not payload_first_chunk:
        assert payload_size == 0
        props = _get_data_chunk_props(
            title="Empty message",
            first_chunk=payload_first_chunk,
            data_size=payload_size,
        )
    elif display_ascii:
        if not is_unambiguous_ascii(payload_first_chunk):
            raise ProcessError(
                "Payload cannot be decoded as ASCII or its decoding leads to a visually ambiguous string"
            )
        props = _get_data_chunk_props(
            title="Message text",
            first_chunk=payload_first_chunk,
            data_size=payload_size,
            max_displayed_size=max_displayed_bytes,
            decoder=lambda chunk: chunk.decode("ascii"),
        )
    else:
        props = _get_data_chunk_props(
            title="Message hex",
            first_chunk=payload_first_chunk,
            data_size=payload_size,
            max_displayed_size=max_displayed_bytes,
        )

    props.append(("Message hash:", payload_hash))

    await confirm_properties(
        "confirm_message_payload",
        title="Confirm message",
        props=props,
        br_code=BRT_Other,
    )


def _get_data_chunk_props(
    title: str,
    first_chunk: bytes,
    data_size: int,
    max_displayed_size: int = _DEFAULT_MAX_DISPLAYED_CHUNK_SIZE,
    decoder: Callable[[bytes], bytes | str] | None = None,
) -> list[PropertyType]:
    displayed_bytes = first_chunk[:max_displayed_size]
    bytes_optional_plural = "byte" if data_size == 1 else "bytes"
    props: list[PropertyType] = [
        (
            f"{title} ({data_size} {bytes_optional_plural}):",
            decoder(displayed_bytes) if decoder else displayed_bytes,
            True,
        )
    ]
    if data_size > max_displayed_size:
        props.append(("...", None, None))

    return props


async def _confirm_tx_data_chunk(
    br_name: str, title: str, first_chunk: bytes, data_size: int
) -> None:
    await confirm_properties(
        br_name,
        title=TR.cardano__confirm_transaction,
        props=_get_data_chunk_props(title, first_chunk, data_size),
        br_code=BRT_Other,
    )


async def show_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = TR.words__address
    await _show_credential(payment_credential, intro_text, purpose="address")
    await _show_credential(stake_credential, intro_text, purpose="address")


async def show_message_header_credentials(credentials: list[Credential]) -> None:
    intro_text = "Address"
    for credential in credentials:
        await _show_credential(credential, intro_text, purpose="message")


async def show_change_output_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
) -> None:
    intro_text = TR.cardano__intro_text_change
    await _show_credential(payment_credential, intro_text, purpose="output")
    await _show_credential(stake_credential, intro_text, purpose="output")


async def show_device_owned_output_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
    show_both_credentials: bool,
) -> None:
    intro_text = TR.cardano__intro_text_owned_by_device
    await _show_credential(payment_credential, intro_text, purpose="output")
    if show_both_credentials:
        await _show_credential(stake_credential, intro_text, purpose="output")


async def show_cvote_registration_payment_credentials(
    payment_credential: Credential,
    stake_credential: Credential,
    show_both_credentials: bool,
    show_payment_warning: bool,
) -> None:
    intro_text = TR.cardano__intro_text_registration_payment

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
    purpose: Literal["address", "output", "cvote_reg_payment_address", "message"],
    extra_text: str | None = None,
) -> None:
    title = {
        "address": f"{ADDRESS_TYPE_NAMES[credential.address_type]} address",
        "output": TR.cardano__confirm_transaction,
        "cvote_reg_payment_address": TR.cardano__confirm_transaction,
        "message": "Confirm message",
    }[purpose]

    props: list[PropertyType] = []
    append = props.append  # local_cache_attribute

    # Credential can be empty in case of enterprise address stake credential
    # and reward address payment credential. In that case we don't want to
    # show some of the "props".
    if credential.is_set():
        credential_title = credential.get_title()
        # TODO: handle translation
        append(
            (
                f"{intro_text} {credential.type_name} credential is a {credential_title}:",
                None,
                None,
            )
        )
        props.extend(credential.format())

    if credential.is_unusual_path:
        append((None, TR.cardano__unusual_path, False))
    if credential.is_mismatch:
        append((None, TR.cardano__credential_mismatch, False))
    if credential.is_reward and purpose != "cvote_reg_payment_address":
        # for cvote registrations, this is handled by extra_text at the end
        append((TR.cardano__reward_address, None, None))
    if credential.is_no_staking:
        append(
            (
                f"{ADDRESS_TYPE_NAMES[credential.address_type]} {TR.cardano__address_no_staking}",
                None,
                None,
            )
        )

    if extra_text:
        append((extra_text, None, None))

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
        TR.cardano__collateral_output_contains_tokens
        if is_collateral_return
        else TR.cardano__transaction_output_contains_tokens
    )
    await confirm_metadata(
        "confirm_tokens",
        TR.cardano__confirm_transaction,
        content,
        br_code=BRT_Other,
    )


async def warn_tx_contains_mint() -> None:
    await confirm_metadata(
        "confirm_tokens",
        TR.cardano__confirm_transaction,
        TR.cardano__transaction_contains_minting_or_burning,
        br_code=BRT_Other,
    )


async def warn_tx_output_no_datum() -> None:
    await confirm_metadata(
        "confirm_no_datum_hash",
        TR.cardano__confirm_transaction,
        TR.cardano__transaction_contains_script_address_no_datum,
        br_code=BRT_Other,
    )


async def warn_no_script_data_hash() -> None:
    await confirm_metadata(
        "confirm_no_script_data_hash",
        TR.cardano__confirm_transaction,
        TR.cardano__transaction_no_script_data_hash,
        br_code=BRT_Other,
    )


async def warn_no_collateral_inputs() -> None:
    await confirm_metadata(
        "confirm_no_collateral_inputs",
        TR.cardano__confirm_transaction,
        TR.cardano__transaction_no_collateral_input,
        br_code=BRT_Other,
    )


async def warn_unknown_total_collateral() -> None:
    await layouts.show_warning(
        "confirm_unknown_total_collateral",
        TR.cardano__unknown_collateral_amount,
        TR.cardano__check_all_items,
        br_code=BRT_Other,
    )


def _get_path_title(path: list[int]) -> str:
    from . import seed

    if seed.is_multisig_path(path):
        return TR.cardano__multisig_path
    elif seed.is_minting_path(path):
        return TR.cardano__token_minting_path
    else:
        return TR.cardano__path


async def confirm_witness_request(
    witness_path: list[int],
) -> None:
    await layouts.confirm_text(
        "confirm_total",
        TR.cardano__confirm_transaction,
        address_n_to_str(witness_path),
        TR.cardano__sign_tx_path_template.format(_get_path_title(witness_path)),
        BRT_Other,
    )


async def confirm_message_path(path: list[int], is_signing_hash: bool) -> None:
    await layouts.confirm_text(
        "confirm_message_signing_path",
        "Confirm message",
        address_n_to_str(path),
        f"Sign message{' hash' if is_signing_hash else ''} with {_get_path_title(path)}:",
        BRT_Other,
    )


async def confirm_tx(
    spending: int,
    fee: int,
    network_id: int,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
) -> None:
    total_amount = format_coin_amount(spending, network_id)
    fee_amount = format_coin_amount(fee, network_id)
    items: list[PropertyType] = [
        (TR.cardano__network, f"{protocol_magics.to_ui_string(protocol_magic)}", True),
        (
            TR.cardano__valid_since,
            f"{format_optional_int(validity_interval_start)}",
            True,
        ),
        (TR.cardano__ttl, f"{format_optional_int(ttl)}", True),
    ]

    await layouts.confirm_cardano_tx(
        total_amount,
        fee_amount,
        items=items,
    )


async def confirm_tx_details(
    network_id: int,
    protocol_magic: int,
    ttl: int | None,
    fee: int | None,
    validity_interval_start: int | None,
    total_collateral: int | None,
    is_network_id_verifiable: bool,
    tx_hash: bytes | None,
) -> None:
    props: list[PropertyType] = []
    append = props.append  # local_cache_attribute

    if fee is not None:
        append(
            (
                f"{TR.words__transaction_fee}:",
                format_coin_amount(fee, network_id),
                False,
            )
        )

    if total_collateral is not None:
        append(
            (
                TR.cardano__total_collateral,
                format_coin_amount(total_collateral, network_id),
                False,
            )
        )

    if is_network_id_verifiable:
        append(
            (
                f"{TR.cardano__network} {protocol_magics.to_ui_string(protocol_magic)}",
                None,
                None,
            )
        )

    append(
        (
            f"{TR.cardano__valid_since} {format_optional_int(validity_interval_start)}",
            None,
            None,
        )
    )
    append((f"{TR.cardano__ttl} {format_optional_int(ttl)}", None, None))

    if tx_hash:
        append((TR.cardano__transaction_id, tx_hash, True))

    if props:
        await confirm_properties(
            "confirm_total",
            TR.cardano__confirm_transaction,
            props,
            hold=True,
            br_code=BRT_Other,
        )


async def confirm_certificate(
    certificate: messages.CardanoTxCertificate, network_id: int
) -> None:
    # stake pool registration requires custom confirmation logic not covered
    # in this call
    assert certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION

    props: list[PropertyType] = [
        (f"{TR.words__confirm}:", CERTIFICATE_TYPE_NAMES[certificate.type], False),
        _format_stake_credential(
            certificate.path, certificate.script_hash, certificate.key_hash
        ),
    ]

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        assert certificate.pool is not None  # validate_certificate
        props.append(
            (TR.cardano__to_pool, format_stake_pool_id(certificate.pool), True)
        )
    elif certificate.type in (
        CardanoCertificateType.STAKE_REGISTRATION_CONWAY,
        CardanoCertificateType.STAKE_DEREGISTRATION_CONWAY,
    ):
        assert certificate.deposit is not None  # validate_certificate
        props.append(
            (
                TR.cardano__deposit,
                format_coin_amount(certificate.deposit, network_id),
                False,
            )
        )

    elif certificate.type == CardanoCertificateType.VOTE_DELEGATION:
        assert certificate.drep is not None  # validate_certificate
        props.append(_format_drep(certificate.drep))

    await confirm_properties(
        "confirm_certificate",
        TR.cardano__confirm_transaction,
        props,
        hold=False,
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
        TR.cardano__confirm_transaction,
        (
            (
                TR.cardano__stake_pool_registration_pool_id,
                format_stake_pool_id(pool_parameters.pool_id),
                True,
            ),
            (TR.cardano__pool_reward_account, pool_parameters.reward_account, True),
            (
                f"{TR.cardano__pledge}: {format_coin_amount(pool_parameters.pledge, network_id)}\n"
                + f"{TR.cardano__cost}: {format_coin_amount(pool_parameters.cost, network_id)}\n"
                + f"{TR.cardano__margin}: {percentage_formatted}%",
                None,
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

    props: list[PropertyType] = []
    if owner.staking_key_path:
        props.append(
            (TR.cardano__pool_owner, address_n_to_str(owner.staking_key_path), True)
        )
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
                None,
            )
        )
    else:
        assert owner.staking_key_hash is not None  # validate_pool_owners
        props.append(
            (
                TR.cardano__pool_owner,
                addresses.derive_human_readable(
                    keychain,
                    messages.CardanoAddressParametersType(
                        address_type=CardanoAddressType.REWARD,
                        staking_key_hash=owner.staking_key_hash,
                    ),
                    protocol_magic,
                    network_id,
                ),
                True,
            )
        )

    await confirm_properties(
        "confirm_pool_owners",
        TR.cardano__confirm_transaction,
        props,
        br_code=BRT_Other,
    )


async def confirm_stake_pool_metadata(
    metadata: messages.CardanoPoolMetadataType | None,
) -> None:
    if metadata is None:
        await confirm_properties(
            "confirm_pool_metadata",
            TR.cardano__confirm_transaction,
            ((TR.cardano__anonymous_pool, None, None),),
            br_code=BRT_Other,
        )
        return

    await confirm_properties(
        "confirm_pool_metadata",
        TR.cardano__confirm_transaction,
        (
            (TR.cardano__pool_metadata_url, metadata.url, True),
            (TR.cardano__pool_metadata_hash, metadata.hash, True),
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
        TR.cardano__confirm_transaction,
        (
            (TR.cardano__confirm_signing_stake_pool, None, None),
            (TR.cardano__network, protocol_magics.to_ui_string(protocol_magic), True),
            (
                TR.cardano__valid_since,
                format_optional_int(validity_interval_start),
                False,
            ),
            (TR.cardano__ttl, format_optional_int(ttl), True),
        ),
        hold=True,
        br_code=BRT_Other,
    )


async def confirm_withdrawal(
    withdrawal: messages.CardanoTxWithdrawal,
    address_bytes: bytes,
    network_id: int,
) -> None:
    address_type_name = (
        TR.cardano__script_reward if withdrawal.script_hash else TR.cardano__reward
    )
    address = addresses.encode_human_readable(address_bytes)
    props: list[PropertyType] = [
        (
            TR.cardano__withdrawal_for_address_template.format(address_type_name),
            address,
            True,
        ),
    ]

    if withdrawal.path:
        props.append(
            _format_stake_credential(
                withdrawal.path, withdrawal.script_hash, withdrawal.key_hash
            )
        )

    props.append(
        (
            f"{TR.words__amount}:",
            format_coin_amount(withdrawal.amount, network_id),
            True,
        )
    )

    await confirm_properties(
        "confirm_withdrawal",
        TR.cardano__confirm_transaction,
        props,
        br_code=BRT_Other,
    )


def _format_stake_credential(
    path: list[int], script_hash: bytes | None, key_hash: bytes | None
) -> PropertyType:
    from .helpers.paths import ADDRESS_INDEX_PATH_INDEX, RECOMMENDED_ADDRESS_INDEX

    if path:
        account_number = format_account_number(path)
        address_index = path[ADDRESS_INDEX_PATH_INDEX]
        if address_index == RECOMMENDED_ADDRESS_INDEX:
            return (
                TR.cardano__for_account_template.format(account_number),
                address_n_to_str(path),
                True,
            )
        return (
            TR.cardano__for_account_and_index_template.format(
                account_number, address_index
            ),
            address_n_to_str(path),
            True,
        )
    elif key_hash:
        return (
            TR.cardano__for_key_hash,
            bech32.encode(bech32.HRP_STAKE_KEY_HASH, key_hash),
            True,
        )
    elif script_hash:
        return (
            TR.cardano__for_script,
            bech32.encode(bech32.HRP_SCRIPT_HASH, script_hash),
            True,
        )
    else:
        # should be unreachable unless there's a bug in validation
        raise ValueError


def _format_drep(drep: messages.CardanoDRep) -> PropertyType:
    if drep.type == CardanoDRepType.KEY_HASH:
        assert drep.key_hash is not None  # validate_drep
        return (
            TR.cardano__delegating_to_key_hash,
            bech32.encode(bech32.HRP_DREP_KEY_HASH, drep.key_hash),
            True,
        )
    elif drep.type == CardanoDRepType.SCRIPT_HASH:
        assert drep.script_hash is not None  # validate_drep
        return (
            TR.cardano__delegating_to_script,
            bech32.encode(bech32.HRP_DREP_SCRIPT_HASH, drep.script_hash),
            True,
        )
    elif drep.type == CardanoDRepType.ABSTAIN:
        return (TR.cardano__delegating_to, TR.cardano__always_abstain, False)
    elif drep.type == CardanoDRepType.NO_CONFIDENCE:
        return (TR.cardano__delegating_to, TR.cardano__always_no_confidence, False)
    else:
        # should be unreachable unless there's a bug in validation
        raise ValueError


async def confirm_cvote_registration_delegation(
    public_key: str,
    weight: int,
) -> None:
    props: list[PropertyType] = [
        (TR.cardano__vote_key_registration, None, None),
        (TR.cardano__delegating_to, public_key, True),
    ]
    if weight is not None:
        props.append((TR.cardano__weight, str(weight), True))

    await confirm_properties(
        "confirm_cvote_registration_delegation",
        title=TR.cardano__confirm_transaction,
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_cvote_registration_payment_address(
    payment_address: str,
    should_show_payment_warning: bool,
) -> None:
    props: list[PropertyType] = [
        (TR.cardano__vote_key_registration, None, None),
        (TR.cardano__rewards_go_to, payment_address, True),
    ]
    if should_show_payment_warning:
        props.append((CVOTE_REWARD_ELIGIBILITY_WARNING, None, None))
    await confirm_properties(
        "confirm_cvote_registration_payment_address",
        title=TR.cardano__confirm_transaction,
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_cvote_registration(
    vote_public_key: str | None,
    staking_path: list[int],
    nonce: int,
    voting_purpose: int | None,
) -> None:
    props: list[PropertyType] = [(TR.cardano__vote_key_registration, None, None)]
    if vote_public_key is not None:
        props.append((TR.cardano__vote_public_key, vote_public_key, True))
    props.extend(
        [
            (
                f"{TR.cardano__staking_key_for_account} {format_account_number(staking_path)}:",
                address_n_to_str(staking_path),
                True,
            ),
            (TR.cardano__nonce, str(nonce), True),
        ]
    )
    if voting_purpose is not None:
        props.append(
            (
                TR.cardano__voting_purpose,
                (
                    TR.cardano__catalyst
                    if voting_purpose == 0
                    else f"{voting_purpose} ({TR.cardano__other})"
                ),
                False,
            )
        )

    await confirm_properties(
        "confirm_cvote_registration",
        title=TR.cardano__confirm_transaction,
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def show_auxiliary_data_hash(auxiliary_data_hash: bytes) -> None:
    await confirm_properties(
        "confirm_auxiliary_data",
        TR.cardano__confirm_transaction,
        ((TR.cardano__auxiliary_data_hash, auxiliary_data_hash, True),),
        br_code=BRT_Other,
    )


async def confirm_token_minting(policy_id: bytes, token: messages.CardanoToken) -> None:
    assert token.mint_amount is not None  # _validate_token
    await confirm_properties(
        "confirm_mint",
        TR.cardano__confirm_transaction,
        (
            (
                TR.cardano__asset_fingerprint,
                format_asset_fingerprint(
                    policy_id,
                    token.asset_name_bytes,
                ),
                True,
            ),
            (
                (
                    TR.cardano__amount_minted_decimals_unknown
                    if token.mint_amount >= 0
                    else TR.cardano__amount_burned_decimals_unknown
                ),
                format_amount(token.mint_amount, 0),
                True,
            ),
        ),
        br_code=BRT_Other,
    )


async def warn_tx_network_unverifiable() -> None:
    await confirm_metadata(
        "warning_no_outputs",
        TR.cardano__warning,
        TR.cardano__no_output_tx,
        br_code=BRT_Other,
    )


async def confirm_script_data_hash(script_data_hash: bytes) -> None:
    await confirm_properties(
        "confirm_script_data_hash",
        TR.cardano__confirm_transaction,
        (
            (
                TR.cardano__script_data_hash,
                bech32.encode(bech32.HRP_SCRIPT_DATA_HASH, script_data_hash),
                True,
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_collateral_input(
    collateral_input: messages.CardanoTxCollateralInput,
) -> None:
    await confirm_properties(
        "confirm_collateral_input",
        TR.cardano__confirm_transaction,
        (
            (TR.cardano__collateral_input_id, collateral_input.prev_hash, True),
            (
                TR.cardano__collateral_input_index,
                str(collateral_input.prev_index),
                True,
            ),
        ),
        br_code=BRT_Other,
    )


async def confirm_reference_input(
    reference_input: messages.CardanoTxReferenceInput,
) -> None:
    await confirm_properties(
        "confirm_reference_input",
        TR.cardano__confirm_transaction,
        (
            (TR.cardano__reference_input_id, reference_input.prev_hash, True),
            (TR.cardano__reference_input_index, str(reference_input.prev_index), True),
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
        TR.cardano__confirm_transaction,
        ((TR.cardano__required_signer, formatted_signer, True),),
        br_code=BRT_Other,
    )


async def show_cardano_address(
    address_parameters: messages.CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
    chunkify: bool,
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
        subtitle=TR.address__coin_address_template.format("ADA"),
        path=path,
        account=account,
        network=network_name,
        chunkify=chunkify,
    )


async def require_confirm_payment_request(
    provider_address: str,
    verified_payment_request: PaymentRequest,
    address_n: Bip32Path | None,
    network_id: int,
) -> None:
    from trezor.ui.layouts import confirm_payment_request

    assert verified_payment_request.amount is not None  # required for non-CoinJoin
    total_amount = format_coin_amount(verified_payment_request.amount, network_id)

    texts: list[tuple[str | None, str]] = []
    refunds: list[tuple[str, str | None, str | None]] = []
    trades: list[tuple[str, str, str, str | None, str | None]] = []
    for memo in verified_payment_request.memos:
        if memo.text_memo is not None:
            texts.append((None, memo.text_memo.text))
        elif memo.text_details_memo is not None:
            texts.append((memo.text_details_memo.title, memo.text_details_memo.text))
        elif memo.refund_memo:
            refund_account_path = address_n_to_str(memo.refund_memo.address_n)
            refunds.append((memo.refund_memo.address, None, refund_account_path))
        elif memo.coin_purchase_memo:
            coin_purchase_account_path = address_n_to_str(
                memo.coin_purchase_memo.address_n
            )
            trades.append(
                (
                    f"-\u00A0{total_amount}",
                    f"+\u00A0{memo.coin_purchase_memo.amount}",
                    memo.coin_purchase_memo.address,
                    None,
                    coin_purchase_account_path,
                )
            )
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    account_path = address_n_to_str(address_n) if address_n else None
    account_items: list[PropertyType] = []
    if account_path:
        account_items.append((TR.address_details__derivation_path, account_path, True))

    await confirm_payment_request(
        verified_payment_request.recipient_name,
        provider_address,
        texts,
        refunds,
        trades,
        account_items,
        None,
        None,
        None,
    )
