from trezor import ui
from trezor.enums import ButtonRequestType, CardanoAddressType, CardanoCertificateType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_metadata,
    confirm_output,
    confirm_path_warning,
    confirm_properties,
)

from apps.common.layout import address_n_to_str

from . import seed
from .address import (
    encode_human_readable_address,
    get_public_key_hash,
    pack_reward_address_bytes,
)
from .helpers import protocol_magics
from .helpers.utils import (
    format_account_number,
    format_asset_fingerprint,
    format_optional_int,
    format_stake_pool_id,
    to_account_path,
)

if False:
    from trezor import wire
    from trezor.messages import (
        CardanoBlockchainPointerType,
        CardanoTxCertificateType,
        CardanoTxWithdrawalType,
        CardanoPoolParametersType,
        CardanoPoolOwnerType,
        CardanoPoolMetadataType,
        CardanoAssetGroupType,
    )

    from trezor.ui.layouts import PropertyType


ADDRESS_TYPE_NAMES = {
    CardanoAddressType.BYRON: "Legacy",
    CardanoAddressType.BASE: "Base",
    CardanoAddressType.POINTER: "Pointer",
    CardanoAddressType.ENTERPRISE: "Enterprise",
    CardanoAddressType.REWARD: "Reward",
}

CERTIFICATE_TYPE_NAMES = {
    CardanoCertificateType.STAKE_REGISTRATION: "Stake key registration",
    CardanoCertificateType.STAKE_DEREGISTRATION: "Stake key deregistration",
    CardanoCertificateType.STAKE_DELEGATION: "Stake delegation",
    CardanoCertificateType.STAKE_POOL_REGISTRATION: "Stakepool registration",
}


def format_coin_amount(amount: int) -> str:
    return "%s %s" % (format_amount(amount, 6), "ADA")


def is_printable_ascii_bytestring(bytestr: bytes) -> bool:
    return all((32 < b < 127) for b in bytestr)


async def confirm_sending(
    ctx: wire.Context,
    ada_amount: int,
    token_bundle: list[CardanoAssetGroupType],
    to: str,
) -> None:
    await confirm_sending_token_bundle(ctx, token_bundle)

    await confirm_output(
        ctx,
        to,
        format_coin_amount(ada_amount),
        title="Confirm transaction",
        subtitle="Confirm sending:",
        font_amount=ui.BOLD,
        width_paginated=17,
        to_str="\nto\n",
        to_paginated=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_sending_token_bundle(
    ctx: wire.Context, token_bundle: list[CardanoAssetGroupType]
) -> None:
    for token_group in token_bundle:
        for token in token_group.tokens:
            await confirm_properties(
                ctx,
                "confirm_token",
                title="Confirm transaction",
                props=[
                    (
                        "Asset fingerprint:",
                        format_asset_fingerprint(
                            policy_id=token_group.policy_id,
                            asset_name_bytes=token.asset_name_bytes,
                        ),
                    ),
                    ("Amount sent:", format_amount(token.amount, 0)),
                ],
                br_code=ButtonRequestType.Other,
            )


async def show_warning_tx_output_contains_tokens(ctx: wire.Context) -> None:
    await confirm_metadata(
        ctx,
        "confirm_tokens",
        title="Confirm transaction",
        content="The following\ntransaction output\ncontains tokens.",
        larger_vspace=True,
        br_code=ButtonRequestType.Other,
    )


async def show_warning_path(ctx: wire.Context, path: list[int], title: str) -> None:
    await confirm_path_warning(ctx, address_n_to_str(path), path_type=title)


async def show_warning_tx_no_staking_info(
    ctx: wire.Context, address_type: CardanoAddressType, amount: int
) -> None:
    atype = ADDRESS_TYPE_NAMES[address_type].lower()
    content = "Change %s address has no stake rights.\nChange amount:\n{}" % atype
    await confirm_metadata(
        ctx,
        "warning_staking",
        title="Confirm transaction",
        content=content,
        param=format_coin_amount(amount),
        hide_continue=True,
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_pointer_address(
    ctx: wire.Context,
    pointer: CardanoBlockchainPointerType,
    amount: int,
) -> None:
    await confirm_properties(
        ctx,
        "warning_pointer",
        title="Confirm transaction",
        props=[
            ("Change address has a\npointer with staking\nrights.\n\n\n", None),
            (
                "Pointer:",
                "%s, %s, %s"
                % (
                    pointer.block_index,
                    pointer.tx_index,
                    pointer.certificate_index,
                ),
            ),
            ("Change amount:", format_coin_amount(amount)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_different_staking_account(
    ctx: wire.Context,
    staking_account_path: list[int],
    amount: int,
) -> None:
    await confirm_properties(
        ctx,
        "warning_differentstaking",
        title="Confirm transaction",
        props=[
            (
                "Change address staking rights do not match the current account.\n\n",
                None,
            ),
            (
                "Staking account %s:" % format_account_number(staking_account_path),
                address_n_to_str(staking_account_path),
            ),
            ("Change amount:", format_coin_amount(amount)),
        ],
        br_code=ButtonRequestType.Other,
    )


async def show_warning_tx_staking_key_hash(
    ctx: wire.Context,
    staking_key_hash: bytes,
    amount: int,
) -> None:
    props = [
        ("Change address staking rights do not match the current account.\n\n", None),
        ("Staking key hash:", staking_key_hash),
        ("Change amount:", format_coin_amount(amount)),
    ]

    await confirm_properties(
        ctx,
        "confirm_different_stakingrights",
        title="Confirm transaction",
        props=props,
        br_code=ButtonRequestType.Other,
    )


async def confirm_transaction(
    ctx: wire.Context,
    amount: int,
    fee: int,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
    is_network_id_verifiable: bool,
) -> None:
    props: list[PropertyType] = [
        ("Transaction amount:", format_coin_amount(amount)),
        ("Transaction fee:", format_coin_amount(fee)),
    ]

    if is_network_id_verifiable:
        props.append(("Network:", protocol_magics.to_ui_string(protocol_magic)))

    props.append(
        ("Valid since: %s" % format_optional_int(validity_interval_start), None)
    )
    props.append(("TTL: %s" % format_optional_int(ttl), None))

    await confirm_properties(
        ctx,
        "confirm_total",
        title="Confirm transaction",
        props=props,
        hold=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificateType
) -> None:
    # stake pool registration requires custom confirmation logic not covered
    # in this call
    assert certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION

    props = [
        ("Confirm:", CERTIFICATE_TYPE_NAMES[certificate.type]),
        (
            "for account %s:" % format_account_number(certificate.path),
            address_n_to_str(to_account_path(certificate.path)),
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
    ctx: wire.Context,
    pool_parameters: CardanoPoolParametersType,
    network_id: int,
    protocol_magic: int,
) -> None:
    margin_percentage = (
        100.0 * pool_parameters.margin_numerator / pool_parameters.margin_denominator
    )
    percentage_formatted = ("%f" % margin_percentage).rstrip("0").rstrip(".")
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
                "Pledge: {}\nCost: {}\nMargin: {}%".format(
                    format_coin_amount(pool_parameters.pledge),
                    format_coin_amount(pool_parameters.cost),
                    percentage_formatted,
                ),
                None,
            ),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_owners(
    ctx: wire.Context,
    keychain: seed.Keychain,
    owners: list[CardanoPoolOwnerType],
    network_id: int,
) -> None:
    props: list[tuple[str, str | None]] = []
    for index, owner in enumerate(owners, 1):
        if owner.staking_key_path:
            props.append(
                ("Pool owner #%d:" % index, address_n_to_str(owner.staking_key_path))
            )
            props.append(
                (
                    encode_human_readable_address(
                        pack_reward_address_bytes(
                            get_public_key_hash(keychain, owner.staking_key_path),
                            network_id,
                        )
                    ),
                    None,
                )
            )
        else:
            assert owner.staking_key_hash is not None  # validate_pool_owners
            props.append(
                (
                    "Pool owner #%d:" % index,
                    encode_human_readable_address(
                        pack_reward_address_bytes(owner.staking_key_hash, network_id)
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


async def confirm_transaction_network_ttl(
    ctx: wire.Context,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
) -> None:
    await confirm_properties(
        ctx,
        "confirm_pool_network",
        title="Confirm transaction",
        props=[
            ("Network:", protocol_magics.to_ui_string(protocol_magic)),
            (
                "Valid since: %s" % format_optional_int(validity_interval_start),
                None,
            ),
            ("TTL: %s" % format_optional_int(ttl), None),
        ],
        br_code=ButtonRequestType.Other,
    )


async def confirm_stake_pool_registration_final(
    ctx: wire.Context,
) -> None:
    await confirm_metadata(
        ctx,
        "confirm_pool_final",
        title="Confirm transaction",
        content="Confirm signing the stake pool registration as an owner",
        hide_continue=True,
        hold=True,
        br_code=ButtonRequestType.Other,
    )


async def confirm_withdrawal(
    ctx: wire.Context, withdrawal: CardanoTxWithdrawalType
) -> None:
    await confirm_properties(
        ctx,
        "confirm_withdrawal",
        title="Confirm transaction",
        props=[
            (
                "Confirm withdrawal\nfor account %s:"
                % format_account_number(withdrawal.path),
                address_n_to_str(to_account_path(withdrawal.path)),
            ),
            ("Amount:", format_coin_amount(withdrawal.amount)),
        ],
        br_code=ButtonRequestType.Other,
    )


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
                "Staking key for account %s:" % format_account_number(staking_path),
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


async def show_warning_address_foreign_staking_key(
    ctx: wire.Context,
    account_path: list[int],
    staking_account_path: list[int],
    staking_key_hash: bytes | None,
) -> None:
    props: list[PropertyType] = [
        (
            "Stake rights associated with this address do not match your account %s:"
            % format_account_number(account_path),
            address_n_to_str(account_path),
        )
    ]

    if staking_account_path:
        props.append(
            (
                "Stake account %s:" % format_account_number(staking_account_path),
                address_n_to_str(staking_account_path),
            )
        )
    else:
        assert staking_key_hash is not None  # _validate_base_address_staking_info
        props.append(("Staking key:", staking_key_hash))
    props.append(("Continue?", None))

    await confirm_properties(
        ctx,
        "warning_foreign_stakingkey",
        title="Warning",
        props=props,
        icon=ui.ICON_WRONG,
        icon_color=ui.RED,
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


async def show_warning_address_pointer(
    ctx: wire.Context, pointer: CardanoBlockchainPointerType
) -> None:
    content = "Pointer address:\nBlock: %s\nTransaction: %s\nCertificate: %s" % (
        pointer.block_index,
        pointer.tx_index,
        pointer.certificate_index,
    )
    await confirm_metadata(
        ctx,
        "warning_pointer",
        title="Warning",
        icon=ui.ICON_WRONG,
        icon_color=ui.RED,
        content=content,
        br_code=ButtonRequestType.Other,
    )
