from ubinascii import hexlify

from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    CardanoAddressType,
    CardanoCertificateType,
)
from trezor.strings import format_amount
from trezor.ui.button import ButtonDefault
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm
from apps.common.layout import address_n_to_str, show_warning

from .helpers import protocol_magics
from .helpers.utils import to_account_path

if False:
    from typing import List
    from trezor import wire
    from trezor.messages import (
        CardanoBlockchainPointerType,
        CardanoTxCertificateType,
        CardanoTxWithdrawalType,
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
}


def format_coin_amount(amount: int) -> str:
    return "%s %s" % (format_amount(amount, 6), "ADA")


async def confirm_sending(ctx: wire.Context, amount: int, to: str):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Confirm sending:")
    t1.bold(format_coin_amount(amount))
    t1.normal("to")

    to_lines = list(chunks(to, 17))
    t1.bold(to_lines[0])

    pages = [t1] + _paginate_lines(to_lines, 1, "Confirm transaction", ui.ICON_SEND)

    await require_confirm(ctx, Paginated(pages))


async def show_warning_tx_no_staking_info(
    ctx: wire.Context, address_type: EnumTypeCardanoAddressType, amount: int
):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Change " + ADDRESS_TYPE_NAMES[address_type].lower())
    t1.normal("address has no stake")
    t1.normal("rights.")
    t1.normal("Change amount:")
    t1.bold(format_coin_amount(amount))

    await require_confirm(ctx, t1)


async def show_warning_tx_pointer_address(
    ctx: wire.Context, pointer: CardanoBlockchainPointerType, amount: int,
):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Change address has a")
    t1.normal("pointer with staking")
    t1.normal("rights.")

    t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t2.normal("Pointer:")
    t2.bold(
        "%s, %s, %s"
        % (pointer.block_index, pointer.tx_index, pointer.certificate_index)
    )
    t2.normal("Change amount:")
    t2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([t1, t2]))


async def show_warning_tx_different_staking_account(
    ctx: wire.Context, staking_account_path: List[int], amount: int,
):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Change address staking")
    t1.normal("rights do not match")
    t1.normal("the current account.")

    t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t2.normal("Staking account:")
    t2.bold(address_n_to_str(staking_account_path))
    t2.normal("Change amount:")
    t2.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([t1, t2]))


async def show_warning_tx_staking_key_hash(
    ctx: wire.Context, staking_key_hash: bytes, amount: int,
):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Change address staking")
    t1.normal("rights do not match")
    t1.normal("the current account.")

    t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t2.normal("Staking key hash:")
    t2.mono(*chunks(hexlify(staking_key_hash), 17))

    t3 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t3.normal("Change amount:")
    t3.bold(format_coin_amount(amount))

    await require_confirm(ctx, Paginated([t1, t2, t3]))


async def confirm_transaction(
    ctx, amount: int, fee: int, protocol_magic: int, has_metadata: bool
) -> None:
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Transaction amount:")
    t1.bold(format_coin_amount(amount))
    t1.normal("Transaction fee:")
    t1.bold(format_coin_amount(fee))

    t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t2.normal("Network:")
    t2.bold(protocol_magics.to_ui_string(protocol_magic))
    if has_metadata:
        t2.normal("Transaction contains")
        t2.normal("metadata")

    await require_hold_to_confirm(ctx, Paginated([t1, t2]))


async def confirm_certificate(
    ctx: wire.Context, certificate: CardanoTxCertificateType
) -> bool:
    pages = []

    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Confirm:")
    t1.bold(CERTIFICATE_TYPE_NAMES[certificate.type])
    t1.normal("for account:")
    t1.bold(address_n_to_str(to_account_path(certificate.path)))
    pages.append(t1)

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
        t2.normal("to pool:")
        t2.bold(hexlify(certificate.pool).decode())
        pages.append(t2)

    await require_confirm(ctx, Paginated(pages))


async def confirm_withdrawal(
    ctx: wire.Context, withdrawal: CardanoTxWithdrawalType
) -> bool:
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Confirm withdrawal")
    t1.normal("for account:")
    t1.bold(address_n_to_str(to_account_path(withdrawal.path)))
    t1.normal("Amount:")
    t1.bold(format_coin_amount(withdrawal.amount))

    await require_confirm(ctx, t1)


async def show_address(
    ctx: wire.Context,
    address: str,
    address_type: EnumTypeCardanoAddressType,
    path: List[int],
    network: int = None,
) -> bool:
    """
    Custom show_address function is needed because cardano addresses don't
    fit on a single screen.
    """
    path_str = address_n_to_str(path)
    t1 = Text(path_str, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        t1.normal("%s network" % protocol_magics.to_ui_string(network))
    t1.normal("%s address" % ADDRESS_TYPE_NAMES[address_type])

    address_lines = list(chunks(address, 17))
    t1.bold(address_lines[0])
    t1.bold(address_lines[1])
    t1.bold(address_lines[2])

    pages = [t1] + _paginate_lines(address_lines, 3, path_str, ui.ICON_RECEIVE)

    return await confirm(
        ctx,
        Paginated(pages),
        code=ButtonRequestType.Address,
        cancel="QR",
        cancel_style=ButtonDefault,
    )


def _paginate_lines(
    lines: List[str], offset: int, desc: str, icon: str, per_page: int = 4
) -> List[ui.Component]:
    pages = []
    if len(lines) > offset:
        to_pages = list(chunks(lines[offset:], per_page))
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
        ctx, staking_key_message, button="Ok",
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
