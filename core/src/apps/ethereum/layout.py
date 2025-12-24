from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_blob,
    confirm_ethereum_staking_tx,
    confirm_text,
    should_show_more,
)

from .helpers import (
    address_from_bytes,
    decode_typed_data,
    format_ethereum_amount,
    get_account_and_path,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Awaitable, Iterable

    from trezor.messages import (
        EthereumFieldType,
        EthereumNetworkInfo,
        EthereumStructMember,
        EthereumTokenInfo,
        PaymentRequest,
    )
    from trezor.ui.layouts import PropertyType


async def require_confirm_approve(
    recipient_str: str | None,
    to_bytes: AnyBytes,
    value: int | None,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    chain_id: int,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo,
    token_address: AnyBytes,
    is_revoke: bool,
    chunkify: bool,
) -> None:
    from trezor.ui.layouts import confirm_ethereum_approve

    from . import networks, tokens

    recipient_addr = address_from_bytes(to_bytes, network)
    chain_id_str = f"{chain_id} ({hex(chain_id)})"
    token_address_str = address_from_bytes(token_address, network)
    total_amount = (
        format_ethereum_amount(value, token, network) if value is not None else None
    )
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_approve(
        recipient_addr,
        recipient_str,
        token is tokens.UNKNOWN_TOKEN,
        token_address_str,
        token.symbol,
        network is networks.UNKNOWN_NETWORK,
        chain_id_str,
        network.name,
        is_revoke,
        total_amount,
        account,
        account_path,
        maximum_fee,
        fee_info_items,
        chunkify=chunkify,
    )


async def require_confirm_tx(
    recipient: str | None,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo | None,
    is_contract_interaction: bool,
    chunkify: bool,
) -> None:
    from trezor.ui.layouts import confirm_ethereum_tx

    total_amount = format_ethereum_amount(value, token, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_tx(
        recipient,
        total_amount,
        account,
        account_path,
        maximum_fee,
        fee_info_items,
        is_contract_interaction,
        chunkify=chunkify,
    )


async def require_confirm_payment_request(
    provider_address: str,
    verified_payment_req: PaymentRequest,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    chain_id: int,
    network: EthereumNetworkInfo,
    token: EthereumTokenInfo | None,
    token_address: str,
) -> None:
    from trezor import wire
    from trezor.ui.layouts import confirm_payment_request
    from trezor.ui.layouts.slip24 import Refund, Trade

    from apps.common.payment_request import parse_amount

    total_amount = format_ethereum_amount(
        parse_amount(verified_payment_req), token, network
    )

    texts = []
    refunds = []
    trades = []
    for memo in verified_payment_req.memos:
        if memo.text_memo is not None:
            texts.append((None, memo.text_memo.text))
        elif memo.text_details_memo is not None:
            texts.append((memo.text_details_memo.title, memo.text_details_memo.text))
        elif memo.refund_memo:
            refund_account, refund_account_path = get_account_and_path(
                memo.refund_memo.address_n
            )
            refunds.append(
                Refund(memo.refund_memo.address, refund_account, refund_account_path)
            )
        elif memo.coin_purchase_memo:
            coin_purchase_account, coin_purchase_account_path = get_account_and_path(
                memo.coin_purchase_memo.address_n
            )
            trades.append(
                Trade(
                    f"- {total_amount}",
                    f"+ {memo.coin_purchase_memo.amount}",
                    memo.coin_purchase_memo.address,
                    coin_purchase_account,
                    coin_purchase_account_path,
                )
            )
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    account, account_path = get_account_and_path(address_n)
    account_items: list[PropertyType] = []
    if account:
        account_items.append((TR.words__account, account, True))
    if account_path:
        account_items.append((TR.address_details__derivation_path, account_path, True))
    if chain_id:
        account_items.append(
            (TR.ethereum__approve_chain_id, f"{network.name} ({chain_id})", True)
        )

    await confirm_payment_request(
        verified_payment_req.recipient_name,
        provider_address,
        texts,
        refunds,
        trades,
        account_items,
        maximum_fee,
        fee_info_items,
        [(TR.ethereum__token_contract, token_address)],
    )


async def require_confirm_stake(
    addr_bytes: bytes,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    total_amount = format_ethereum_amount(value, None, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_stake,  # title
        TR.ethereum__staking_stake_intro,  # intro_question
        TR.ethereum__staking_stake,  # verb
        total_amount,
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_stake_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_unstake(
    addr_bytes: bytes,
    value: int,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    total_amount = format_ethereum_amount(value, None, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_unstake,  # title
        TR.ethereum__staking_unstake_intro,  # intro_question
        TR.ethereum__staking_unstake,  # verb
        total_amount,
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_stake_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_claim(
    addr_bytes: bytes,
    address_n: list[int],
    maximum_fee: str,
    fee_info_items: Iterable[PropertyType],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:

    addr_str = address_from_bytes(addr_bytes, network)
    account, account_path = get_account_and_path(address_n)

    await confirm_ethereum_staking_tx(
        TR.ethereum__staking_claim,  # title
        TR.ethereum__staking_claim_intro,  # intro_question
        TR.ethereum__staking_claim,  # verb
        "",  # total_amount
        account,
        account_path,
        maximum_fee,
        addr_str,  # address
        TR.ethereum__staking_claim_address,  # address_title
        fee_info_items,  # info_items
        chunkify=chunkify,
    )


async def require_confirm_unknown_token(title: str) -> None:
    from trezor.ui.layouts import confirm_ethereum_unknown_contract_warning

    await confirm_ethereum_unknown_contract_warning(title)


def require_confirm_address(
    address_bytes: bytes,
    title: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    br_name: str | None = None,
    warning_footer: str | None = None,
) -> Awaitable[None]:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_address

    address_hex = "0x" + hexlify(address_bytes).decode()
    return confirm_address(
        title or TR.ethereum__title_signing_address,
        address_hex,
        subtitle=subtitle,
        verb=verb,
        warning_footer=warning_footer,
        br_name=br_name,
        br_code=ButtonRequestType.SignTx,
    )


def require_confirm_other_data(data: AnyBytes, data_total: int) -> Awaitable[None]:
    return confirm_blob(
        "confirm_data",
        TR.ethereum__title_input_data,
        data,
        description=TR.ethereum__data_size_template.format(data_total),
        subtitle=TR.ethereum__title_all_input_data_template.format(data_total),
        verb=TR.buttons__confirm,
        verb_cancel=TR.send__cancel_sign,
        br_code=ButtonRequestType.SignTx,
        ask_pagination=True,
    )


async def confirm_message_hash(message_hash: bytes) -> None:
    from ubinascii import hexlify

    from trezor.ui.layouts import confirm_value

    message_hash_hex = "0x" + hexlify(message_hash).decode()

    await confirm_value(
        TR.ethereum__title_confirm_message_hash,
        message_hash_hex,
        "",
        "confirm_message_hash",
        verb=TR.buttons__confirm,
        br_code=ButtonRequestType.SignTx,
        cancel=True,
    )


async def confirm_typed_data_final() -> None:
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "confirm_typed_data_final",
        TR.ethereum__title_confirm_typed_data,
        TR.ethereum__sign_eip712,
        verb=TR.buttons__hold_to_confirm,
        hold=True,
    )


def confirm_empty_typed_message() -> Awaitable[None]:
    return confirm_text(
        "confirm_empty_typed_message",
        TR.ethereum__title_confirm_message,
        "",
        TR.ethereum__no_message_field,
    )


async def should_show_domain(name: AnyBytes, version: AnyBytes) -> bool:
    domain_name = decode_typed_data(name, "string")
    domain_version = decode_typed_data(version, "string")

    para = (
        (TR.ethereum__name_and_version, False),
        (domain_name, False),
        (domain_version, False),
    )
    return await should_show_more(
        TR.ethereum__title_confirm_domain,
        para,
        TR.ethereum__show_full_domain,
        "should_show_domain",
    )


async def should_show_struct(
    description: str,
    data_members: list[EthereumStructMember],
    title: str | None = None,
    button_text: str | None = None,
) -> bool:
    from trezor.strings import format_plural

    title = title or TR.ethereum__title_confirm_struct  # def_arg
    button_text = button_text or TR.ethereum__show_full_struct  # def_arg

    plural = format_plural(
        "{count} {plural}", len(data_members), TR.plurals__contains_x_keys
    )
    contains_plural = f"{TR.words__contains} {plural}"

    para = (
        (description, False),
        (contains_plural, False),
        (", ".join(field.name for field in data_members), False),
    )
    return await should_show_more(
        title,
        para,
        button_text,
        "should_show_struct",
    )


async def should_show_array(
    parent_objects: Iterable[str],
    data_type: str,
    size: int,
) -> bool:
    from trezor.strings import format_plural_english

    # Leaving english plural form because of dynamic noun - data_type
    plural = format_plural_english("{count} {plural}", size, data_type)
    array_of_plural = f"{TR.words__array_of} {plural}"
    para = ((array_of_plural, False),)
    return await should_show_more(
        limit_str(".".join(parent_objects)),
        para,
        TR.ethereum__show_full_array,
        "should_show_array",
    )


async def confirm_typed_value(
    name: str,
    value: AnyBytes,
    parent_objects: list[str],
    field: EthereumFieldType,
    array_index: int | None = None,
) -> None:
    from trezor.enums import EthereumDataType

    from .helpers import get_type_name

    type_name = get_type_name(field)

    if array_index is not None:
        title = limit_str(".".join(parent_objects + [name]))
        description = f"[{array_index}] ({type_name})"
    else:
        title = limit_str(".".join(parent_objects))
        description = f"{name} ({type_name})"

    data = decode_typed_data(value, type_name)

    if field.data_type in (EthereumDataType.ADDRESS, EthereumDataType.BYTES):
        await confirm_blob(
            "confirm_typed_value",
            title,
            data,
            description,
        )
    else:
        await confirm_text(
            "confirm_typed_value",
            title,
            data,
            description,
        )


def limit_str(s: str, limit: int = 16) -> str:
    """Shortens string to show the last <limit> characters."""
    if len(s) <= limit + 2:
        return s

    return ".." + s[-limit:]
