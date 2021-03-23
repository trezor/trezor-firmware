import math
from ubinascii import hexlify

from trezor import ui
from trezor.enums import ButtonRequestType, CardanoAddressType, CardanoCertificateType
from trezor.strings import format_amount
from trezor.ui.components.tt.button import ButtonDefault
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text
from trezor.utils import chunks

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm
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

# Maximum number of characters per line in monospace font.
_MAX_MONO_LINE = 18


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

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm sending:")
    page1.bold(format_coin_amount(ada_amount))
    page1.normal("to")

    pages = _paginate_text(
        page1,
        "Confirm transaction",
        ui.ICON_SEND,
        to,
        lines_per_page=4,
        lines_used_on_first_page=3,
    )

    await require_confirm(ctx, Paginated(pages))


async def confirm_sending_token_bundle(
    ctx: wire.Context, token_bundle: list[CardanoAssetGroupType]
) -> None:
    for token_group in token_bundle:
        for token in token_group.tokens:
            page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
            page1.normal("Asset fingerprint:")
            page1.bold(
                format_asset_fingerprint(
                    policy_id=token_group.policy_id,
                    asset_name_bytes=token.asset_name_bytes,
                )
            )
            page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
            page2.normal("Amount sent:")
            page2.bold(format_amount(token.amount, 0))
            await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_output_contains_tokens(ctx: wire.Context) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("The following")
    page1.normal("transaction output")
    page1.normal("contains tokens.")
    page1.br_half()
    page1.normal("Continue?")

    await require_confirm(ctx, page1)


async def show_warning_path(ctx: wire.Context, path: list[int], title: str) -> None:
    page1 = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    page1.normal(title)
    page1.bold(address_n_to_str(path))
    page1.normal("is unknown.")
    page1.normal("Are you sure?")
    await require_confirm(ctx, page1)


async def show_warning_tx_no_staking_info(
    ctx: wire.Context, address_type: CardanoAddressType, amount: int
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change " + ADDRESS_TYPE_NAMES[address_type].lower())
    page1.normal("address has no stake")
    page1.normal("rights.")
    page1.normal("Change amount:")
    page1.bold(format_coin_amount(amount))

    await require_confirm(ctx, page1)


async def show_warning_tx_pointer_address(
    ctx: wire.Context,
    pointer: CardanoBlockchainPointerType,
    amount: int,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address has a")
    page1.normal("pointer with staking")
    page1.normal("rights.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Pointer:")
    page2.bold(
        "%s, %s, %s"
        % (pointer.block_index, pointer.tx_index, pointer.certificate_index)
    )
    page2.normal("Change amount:")
    page2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_different_staking_account(
    ctx: wire.Context,
    staking_account_path: list[int],
    amount: int,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address staking")
    page1.normal("rights do not match")
    page1.normal("the current account.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Staking account %s:" % format_account_number(staking_account_path))
    page2.bold(address_n_to_str(staking_account_path))
    page2.normal("Change amount:")
    page2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_staking_key_hash(
    ctx: wire.Context,
    staking_key_hash: bytes,
    amount: int,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address staking")
    page1.normal("rights do not match")
    page1.normal("the current account.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Staking key hash:")
    page2.mono(*chunks(hexlify(staking_key_hash).decode(), 17))

    page3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page3.normal("Change amount:")
    page3.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([page1, page2, page3]))


async def confirm_transaction(
    ctx: wire.Context,
    amount: int,
    fee: int,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
    is_network_id_verifiable: bool,
) -> None:
    pages: list[ui.Component] = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Transaction amount:")
    page1.bold(format_coin_amount(amount))
    page1.normal("Transaction fee:")
    page1.bold(format_coin_amount(fee))
    pages.append(page1)

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    if is_network_id_verifiable:
        page2.normal("Network:")
        page2.bold(protocol_magics.to_ui_string(protocol_magic))
    page2.normal("Valid since: %s" % format_optional_int(validity_interval_start))
    page2.normal("TTL: %s" % format_optional_int(ttl))
    pages.append(page2)

    await require_hold_to_confirm(ctx, Paginated(pages))


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificateType
) -> None:
    # stake pool registration requires custom confirmation logic not covered
    # in this call
    assert certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION

    pages: list[ui.Component] = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm:")
    page1.bold(CERTIFICATE_TYPE_NAMES[certificate.type])
    page1.normal("for account %s:" % format_account_number(certificate.path))
    page1.bold(address_n_to_str(to_account_path(certificate.path)))
    pages.append(page1)

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        assert certificate.pool is not None  # validate_certificate
        page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page2.normal("to pool:")
        page2.bold(format_stake_pool_id(certificate.pool))
        pages.append(page2)

    await require_confirm(ctx, Paginated(pages))


async def confirm_stake_pool_parameters(
    ctx: wire.Context,
    pool_parameters: CardanoPoolParametersType,
    network_id: int,
    protocol_magic: int,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.bold("Stake pool registration")
    page1.normal("Pool ID:")
    page1.bold(format_stake_pool_id(pool_parameters.pool_id))

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Pool reward account:")
    page2.bold(pool_parameters.reward_account)

    page3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page3.normal("Pledge: " + format_coin_amount(pool_parameters.pledge))
    page3.normal("Cost: " + format_coin_amount(pool_parameters.cost))
    margin_percentage = (
        100.0 * pool_parameters.margin_numerator / pool_parameters.margin_denominator
    )
    percentage_formatted = ("%f" % margin_percentage).rstrip("0").rstrip(".")
    page3.normal("Margin: %s%%" % percentage_formatted)

    await require_confirm(ctx, Paginated([page1, page2, page3]))


async def confirm_stake_pool_owners(
    ctx: wire.Context,
    keychain: seed.Keychain,
    owners: list[CardanoPoolOwnerType],
    network_id: int,
) -> None:
    pages: list[ui.Component] = []
    for index, owner in enumerate(owners, 1):
        page = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page.normal("Pool owner #%d:" % (index))

        if owner.staking_key_path:
            page.bold(address_n_to_str(owner.staking_key_path))
            page.normal(
                encode_human_readable_address(
                    pack_reward_address_bytes(
                        get_public_key_hash(keychain, owner.staking_key_path),
                        network_id,
                    )
                )
            )
        else:
            assert owner.staking_key_hash is not None  # validate_pool_owners
            page.bold(
                encode_human_readable_address(
                    pack_reward_address_bytes(owner.staking_key_hash, network_id)
                )
            )

        pages.append(page)

    await require_confirm(ctx, Paginated(pages))


async def confirm_stake_pool_metadata(
    ctx: wire.Context,
    metadata: CardanoPoolMetadataType | None,
) -> None:

    if metadata is None:
        page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page1.normal("Pool has no metadata")
        page1.normal("(anonymous pool)")

        await require_confirm(ctx, page1)
        return

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Pool metadata url:")
    page1.bold(metadata.url)

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Pool metadata hash:")
    page2.bold(hexlify(metadata.hash).decode())

    await require_confirm(ctx, Paginated([page1, page2]))


async def confirm_transaction_network_ttl(
    ctx: wire.Context,
    protocol_magic: int,
    ttl: int | None,
    validity_interval_start: int | None,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Network:")
    page1.bold(protocol_magics.to_ui_string(protocol_magic))
    page1.normal("Valid since: %s" % format_optional_int(validity_interval_start))
    page1.normal("TTL: %s" % format_optional_int(ttl))

    await require_confirm(ctx, page1)


async def confirm_stake_pool_registration_final(
    ctx: wire.Context,
) -> None:

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm signing the stake pool registration as an owner")

    await require_hold_to_confirm(ctx, page1)


async def confirm_withdrawal(
    ctx: wire.Context, withdrawal: CardanoTxWithdrawalType
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm withdrawal")
    page1.normal("for account %s:" % format_account_number(withdrawal.path))
    page1.bold(address_n_to_str(to_account_path(withdrawal.path)))
    page1.normal("Amount:")
    page1.bold(format_coin_amount(withdrawal.amount))

    await require_confirm(ctx, page1)


async def confirm_catalyst_registration(
    ctx: wire.Context,
    public_key: str,
    staking_path: list[int],
    reward_address: str,
    nonce: int,
) -> None:
    pages: list[ui.Component] = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.bold("Catalyst voting key")
    page1.bold("registration")
    pages.append(page1)

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Voting public key:")
    page2.bold(*chunks(public_key, 17))
    pages.append(page2)

    page3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page3.normal("Staking key for")
    page3.normal("account %s:" % format_account_number(staking_path))
    page3.bold(address_n_to_str(staking_path))
    pages.append(page3)

    page4 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page4.normal("Rewards go to:")

    pages.extend(
        _paginate_text(page4, "Confirm transaction", ui.ICON_SEND, reward_address)
    )

    last_page = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    last_page.normal("Nonce: %s" % nonce)
    pages.append(last_page)

    await require_confirm(ctx, Paginated(pages))


async def show_auxiliary_data_hash(
    ctx: wire.Context, auxiliary_data_hash: bytes
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Auxiliary data hash:")
    page1.bold(hexlify(auxiliary_data_hash).decode())

    await require_confirm(ctx, page1)


async def show_address(
    ctx: wire.Context,
    address: str,
    address_type: CardanoAddressType,
    path: list[int],
    network: str | None = None,
) -> bool:
    """
    Custom show_address function is needed because cardano addresses don't
    fit on a single screen.
    """

    address_type_label = "%s address" % ADDRESS_TYPE_NAMES[address_type]
    page1 = Text(address_type_label, ui.ICON_RECEIVE, ui.GREEN)

    lines_per_page = 5
    lines_used_on_first_page = 0

    # assemble first page to be displayed (path + network + whatever part of the address fits)
    if network is not None:
        page1.normal("%s network" % network)
        lines_used_on_first_page += 1

    path_str = address_n_to_str(path)
    page1.mono(path_str)
    lines_used_on_first_page = min(
        lines_used_on_first_page + math.ceil(len(path_str) / _MAX_MONO_LINE),
        lines_per_page,
    )

    pages = _paginate_text(
        page1,
        address_type_label,
        ui.ICON_RECEIVE,
        address,
        lines_per_page=lines_per_page,
        lines_used_on_first_page=lines_used_on_first_page,
    )

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


def _paginate_text(
    first_page: Text,
    page_desc: str,
    page_icon: str,
    text: str,
    lines_per_page: int = 5,
    lines_used_on_first_page: int = 1,
) -> list[ui.Component]:
    lines = list(chunks(text, 17))

    offset = lines_per_page - lines_used_on_first_page

    for text_line in lines[:offset]:
        first_page.bold(text_line)

    pages: list[ui.Component] = [first_page]
    if len(lines) > offset:
        to_pages = list(chunks(lines[offset:], lines_per_page))
        for page in to_pages:
            t = Text(page_desc, page_icon, ui.GREEN)
            for line in page:
                t.bold(line)
            pages.append(t)

    return pages


async def show_warning_address_foreign_staking_key(
    ctx: wire.Context,
    account_path: list[int],
    staking_account_path: list[int],
    staking_key_hash: bytes | None,
) -> None:
    page1 = Text("Warning", ui.ICON_WRONG, ui.RED)
    page1.normal("Stake rights associated")
    page1.normal("with this address do")
    page1.normal("not match your")
    page1.normal("account %s:" % format_account_number(account_path))
    page1.bold(address_n_to_str(account_path))

    page2 = Text("Warning", ui.ICON_WRONG, ui.RED)
    if staking_account_path:
        page2.normal("Stake account %s:" % format_account_number(staking_account_path))
        page2.bold(address_n_to_str(staking_account_path))
        page2.br_half()
    else:
        assert staking_key_hash is not None  # _validate_base_address_staking_info
        page2.normal("Staking key:")
        page2.bold(hexlify(staking_key_hash).decode())
    page2.normal("Continue?")

    await require_confirm(ctx, Paginated([page1, page2]))


async def show_warning_tx_network_unverifiable(ctx: wire.Context) -> None:
    page1 = Text("Warning", ui.ICON_SEND, ui.GREEN)
    page1.normal("Transaction has no outputs, network cannot be verified.")
    page1.br_half()
    page1.normal("Continue?")

    await require_confirm(ctx, page1)


async def show_warning_address_pointer(
    ctx: wire.Context, pointer: CardanoBlockchainPointerType
) -> None:
    text = Text("Warning", ui.ICON_WRONG, ui.RED)
    text.normal("Pointer address:")
    text.normal("Block: %s" % pointer.block_index)
    text.normal("Transaction: %s" % pointer.tx_index)
    text.normal("Certificate: %s" % pointer.certificate_index)
    text.normal("Continue?")
    await require_confirm(ctx, text)
