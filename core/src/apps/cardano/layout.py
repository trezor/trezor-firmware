import math
from ubinascii import hexlify

from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
    CardanoPoolMetadataType,
    CardanoPoolOwnerType,
)
from trezor.strings import format_amount
from trezor.ui.button import ButtonDefault
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm
from apps.common.layout import address_n_to_str, show_warning

from . import seed
from .address import (
    encode_human_readable_address,
    get_public_key_hash,
    pack_reward_address_bytes,
)
from .helpers import protocol_magics
from .helpers.utils import to_account_path

if False:
    from typing import List, Optional
    from trezor import wire
    from trezor.messages import (
        CardanoBlockchainPointerType,
        CardanoTxCertificateType,
        CardanoTxWithdrawalType,
        CardanoPoolParametersType,
    )
    from trezor.messages.CardanoAddressParametersType import EnumTypeCardanoAddressType


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


async def confirm_sending(ctx: wire.Context, amount: int, to: str) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm sending:")
    page1.bold(format_coin_amount(amount))
    page1.normal("to")

    to_lines = list(chunks(to, 17))
    page1.bold(to_lines[0])

    pages = [page1] + _paginate_lines(to_lines, 1, "Confirm transaction", ui.ICON_SEND)

    await require_confirm(ctx, Paginated(pages))


async def show_warning_tx_no_staking_info(
    ctx: wire.Context, address_type: EnumTypeCardanoAddressType, amount: int
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
    staking_account_path: List[int],
    amount: int,
) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Change address staking")
    page1.normal("rights do not match")
    page1.normal("the current account.")

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Staking account:")
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
    ctx, amount: int, fee: int, protocol_magic: int, ttl: int, has_metadata: bool
) -> None:
    pages = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Transaction amount:")
    page1.bold(format_coin_amount(amount))
    page1.normal("Transaction fee:")
    page1.bold(format_coin_amount(fee))
    pages.append(page1)

    page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page2.normal("Network:")
    page2.bold(protocol_magics.to_ui_string(protocol_magic))
    page2.normal("Transaction TTL:")
    page2.bold(str(ttl))
    pages.append(page2)

    if has_metadata:
        page3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page3.normal("Transaction contains")
        page3.normal("metadata")
        pages.append(page3)

    await require_hold_to_confirm(ctx, Paginated(pages))


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificateType
) -> None:
    # stake pool registration requires custom confirmation logic not covered
    # in this call
    assert certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION

    pages = []

    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Confirm:")
    page1.bold(CERTIFICATE_TYPE_NAMES[certificate.type])
    page1.normal("for account:")
    page1.bold(address_n_to_str(to_account_path(certificate.path)))
    pages.append(page1)

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        page2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        page2.normal("to pool:")
        page2.bold(hexlify(certificate.pool).decode())
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
    page1.normal("Pool id:")
    page1.bold(hexlify(pool_parameters.pool_id).decode())

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
    keychain: seed.keychain,
    owners: List[CardanoPoolOwnerType],
    network_id: int,
) -> None:
    pages = []
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
            page.bold(
                encode_human_readable_address(
                    pack_reward_address_bytes(owner.staking_key_hash, network_id)
                )
            )

        pages.append(page)

    await require_confirm(ctx, Paginated(pages))


async def confirm_stake_pool_metadata(
    ctx: wire.Context,
    metadata: Optional[CardanoPoolMetadataType],
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


async def confirm_transaction_network_ttl(ctx, protocol_magic: int, ttl: int) -> None:
    page1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    page1.normal("Network:")
    page1.bold(protocol_magics.to_ui_string(protocol_magic))
    page1.normal("Transaction TTL:")
    page1.bold(str(ttl))

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
    page1.normal("for account:")
    page1.bold(address_n_to_str(to_account_path(withdrawal.path)))
    page1.normal("Amount:")
    page1.bold(format_coin_amount(withdrawal.amount))

    await require_confirm(ctx, page1)


async def show_address(
    ctx: wire.Context,
    address: str,
    address_type: EnumTypeCardanoAddressType,
    path: List[int],
    network: str = None,
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

    address_lines = list(chunks(address, 17))
    for address_line in address_lines[: lines_per_page - lines_used_on_first_page]:
        page1.bold(address_line)

    # append remaining pages containing the rest of the address
    pages = [page1] + _paginate_lines(
        address_lines,
        lines_per_page - lines_used_on_first_page,
        address_type_label,
        ui.ICON_RECEIVE,
        lines_per_page,
    )

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


def _paginate_lines(
    lines: List[str], offset: int, desc: str, icon: str, lines_per_page: int = 4
) -> List[ui.Component]:
    pages = []
    if len(lines) > offset:
        to_pages = list(chunks(lines[offset:], lines_per_page))
        for page in to_pages:
            t = Text(desc, icon, ui.GREEN)
            for line in page:
                t.bold(line)
            pages.append(t)

    return pages


async def show_warning_address_foreign_staking_key(
    ctx: wire.Context,
    account_path: List[int],
    staking_account_path: List[int],
    staking_key_hash: bytes,
) -> None:
    await show_warning(
        ctx,
        (
            "Stake rights associated",
            "with this address do",
            "not match your",
            "account",
            address_n_to_str(account_path),
        ),
        button="Ok",
    )

    if staking_account_path:
        staking_key_message = (
            "Stake account path:",
            address_n_to_str(staking_account_path),
        )
    else:
        staking_key_message = ("Staking key:", hexlify(staking_key_hash).decode())

    await show_warning(
        ctx,
        staking_key_message,
        button="Ok",
    )


async def show_warning_address_pointer(
    ctx: wire.Context, pointer: CardanoBlockchainPointerType
) -> None:
    await show_warning(
        ctx,
        (
            "Pointer address:",
            "Block: %s" % pointer.block_index,
            "Transaction: %s" % pointer.tx_index,
            "Certificate: %s" % pointer.certificate_index,
        ),
        button="Ok",
    )
