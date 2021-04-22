from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.components.tt.text import Text
from trezor.ui.components.tt.scroll import Paginated
from trezor.utils import chunks

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm
from apps.common.layout import split_address

from . import networks, tokens
from .address import address_from_bytes
from .abi import abi_decode_single, is_array, typeof_array, parse_array_n


async def confirm_typed_domain_brief(ctx, domain_values: dict):
    page = Text("Typed Data", ui.ICON_SEND, icon_color=ui.GREEN)

    domain_name = abi_decode_single("string", domain_values.get("name"))
    domain_version = abi_decode_single("string", domain_values.get("version"))

    page.bold("%s" % domain_name)
    page.normal("%s" % domain_version)
    page.br()
    page.mono("View EIP712Domain?")

    return await confirm(ctx, page, ButtonRequestType.Other)


async def require_confirm_typed_domain(ctx, domain_types: dict, domain_values: dict):
    def make_field_page(title, field_name, type_name, field_value):
        page = Text(title, ui.ICON_CONFIG, icon_color=ui.ORANGE_ICON)
        page.bold("%s (%s)" % (field_name, type_name))
        page.mono(*split_data("{}".format(field_value), 17))
        return page

    pages = []
    for type_def in domain_types:
        value = domain_values.get(type_def["name"])
        pages.append(make_field_page(
            title="EIP712Domain %d/%d" % (len(pages)+1, len(domain_types)),
            field_name=limit_str(type_def["name"]),
            type_name=limit_str(type_def["type"]),
            field_value=abi_decode_single(type_def["type"], value),
        ))

    return await require_hold_to_confirm(
        ctx, Paginated(pages), ButtonRequestType.ConfirmOutput
    )


TYPED_DATA_BRIEF_FIELDS = 3


async def confirm_typed_data_brief(ctx, primary_type: str, fields: []):
    page = Text(primary_type, ui.ICON_SEND, icon_color=ui.GREEN)

    limit = TYPED_DATA_BRIEF_FIELDS
    for field in fields:
        page.bold("%s" % limit_str(field["name"]))
        limit -= 1
        if limit == 0:
            break

    printed_num = (TYPED_DATA_BRIEF_FIELDS - limit)
    if printed_num < len(fields):
        page.mono("...and %d more." % (len(fields) - printed_num))

    page.mono("View full message?")

    return await confirm(ctx, page, ButtonRequestType.Other)


async def require_confirm_typed_data(ctx, primary_type: str, data_types: dict, data_values: dict):
    def make_type_page(root_name, field_name, current_array_offsets, current_field, total_fields):
        array_offsets = ""
        for offset in current_array_offsets:
            array_offsets += "%d." % offset

        if len(array_offsets) > 0:
            title = limit_str("%s.%s%s" % (root_name, array_offsets, field_name), 13)
        else:
            title = limit_str("%s.%s" % (root_name, field_name), 13)

        if len(array_offsets) == 0:
            title += " %d/%d" % (current_field+1, total_fields)

        return Text(title, ui.ICON_CONFIG, icon_color=ui.ORANGE_ICON)

    async def confirm_struct(root_name, type_name: str, values: dict, array_offsets: list, hold: bool = False):
        current_type = type_name
        current_root_name = root_name
        type_def = data_types[current_type]

        type_view_pages = []

        for (field_idx, field) in enumerate(type_def):
            current_type = field["type"]
            current_value = values.get(field["name"])

            if is_array(current_type):
                array_preview_page = make_type_page(
                    root_name=current_root_name,
                    field_name=field["name"],
                    current_array_offsets=array_offsets,
                    current_field=field_idx,
                    total_fields=len(type_def),
                )

                array_view_page = make_type_page(
                    root_name=current_root_name,
                    field_name=field["name"],
                    current_array_offsets=array_offsets,
                    current_field=field_idx,
                    total_fields=len(type_def),
                )

                array_len = len(current_value)
                array_preview_page.bold(limit_str(field["type"]))
                array_preview_page.mono("Contains %d elem%s." % (array_len, "s" if array_len > 1 else ""))
                array_preview_page.br()
                array_preview_page.mono("View data?")

                array_view_page.bold(limit_str(field["type"]))
                array_view_page.mono("Contains %d elem%s." % (array_len, "s" if array_len > 1 else ""))
                type_view_pages.append(array_view_page)

                go_deeper = await confirm(ctx, array_preview_page, ButtonRequestType.ConfirmOutput)
                if go_deeper:
                    for array_offset in range(0, len(current_value)):
                        await confirm_struct(
                            root_name=field["name"],
                            type_name=typeof_array(current_type),
                            values=current_value[array_offset],
                            array_offsets=array_offsets + [array_offset],
                            hold=False,
                        )
                        continue

                continue

            type_view_page = make_type_page(
                root_name=current_root_name,
                field_name=field["name"],
                current_array_offsets=array_offsets,
                current_field=field_idx,
                total_fields=len(type_def),
            )
            if current_type in data_types:
                type_preview_page = make_type_page(
                    root_name=current_root_name,
                    field_name=field["name"],
                    current_array_offsets=array_offsets,
                    current_field=field_idx,
                    total_fields=len(type_def),
                )

                fields_num = len(data_types[current_type])
                type_preview_page.bold(limit_str(current_type))
                type_preview_page.mono("Contains %d field%s." % (fields_num, "s" if fields_num > 1 else ""))
                type_preview_page.br()
                type_preview_page.mono("View data?")

                type_view_page.bold(limit_str(current_type))
                type_view_page.mono("Contains %d field%s." % (fields_num, "s" if fields_num > 1 else ""))
                type_view_pages.append(type_view_page)

                go_deeper = await confirm(ctx, type_preview_page, ButtonRequestType.ConfirmOutput)
                if go_deeper:
                    await confirm_struct(
                        root_name=field["name"],
                        type_name=current_type,
                        values=current_value,
                        array_offsets=[],
                        hold=False,
                    )

            else:
                type_view_page.bold(current_type)
                value_decoded = abi_decode_single(current_type, current_value)
                type_view_page.mono(*split_data(value_decoded, 17))
                type_view_pages.append(type_view_page)

        if hold:
            return await require_hold_to_confirm(
                ctx,
                Paginated(type_view_pages) if len(type_view_pages) > 1 else type_view_pages[0],
                ButtonRequestType.ConfirmOutput,
            )
        return await require_confirm(
            ctx,
            Paginated(type_view_pages) if len(type_view_pages) > 1 else type_view_pages[0],
            ButtonRequestType.ConfirmOutput,
        )

    await confirm_struct(
        root_name=primary_type,
        type_name=primary_type,
        values=data_values,
        array_offsets=[],
        hold=True,
    )


async def require_confirm_typed_data_hash(ctx, primary_type: str, typed_data_hash: bytes):
    text = Text("Sign typed data?", ui.ICON_CONFIG, icon_color=ui.GREEN, new_lines=False)
    text.bold(limit_str(primary_type))
    text.mono(*split_data("0x%s" % hexlify(typed_data_hash).decode()))

    return await require_hold_to_confirm(
        ctx, text, ButtonRequestType.ConfirmOutput
    )


async def require_confirm_tx(ctx, to_bytes, value, chain_id, token=None, tx_type=None):
    if to_bytes:
        to_str = address_from_bytes(to_bytes, networks.by_chain_id(chain_id))
    else:
        to_str = "new contract?"
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.bold(format_ethereum_amount(value, token, chain_id, tx_type))
    text.normal(ui.GREY, " to ", ui.FG)
    for to_line in split_address(to_str):
        text.br()
        text.mono(to_line)
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_fee(
    ctx, spending, gas_price, gas_limit, chain_id, token=None, tx_type=None
):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.bold(format_ethereum_amount(spending, token, chain_id, tx_type))
    text.normal(" ", ui.GREY, "Gas price:", ui.FG)
    text.bold(format_ethereum_amount(gas_price, None, chain_id, tx_type))
    text.normal(" ", ui.GREY, "Maximum fee:", ui.FG)
    text.bold(format_ethereum_amount(gas_price * gas_limit, None, chain_id, tx_type))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_unknown_token(ctx, address_bytes):
    text = Text("Unknown token", ui.ICON_SEND, ui.ORANGE, new_lines=False)
    text.normal(ui.GREY, "Contract:", ui.FG)
    contract_address_hex = "0x" + hexlify(address_bytes).decode()
    text.mono(*split_data(contract_address_hex))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


def split_data(data, width: int = 18):
    return chunks(data, width)


def limit_str(s: str, limit: int = 16) -> str:
    if len(s) <= limit+2:
        return s

    return s[:limit] + ".."


def limit_left_str(s: str, limit: int = 16) -> str:
    if len(s) <= limit+2:
        return s

    return ".." + s[(len(s) - limit):]


async def require_confirm_data(ctx, data, data_total):
    data_str = hexlify(data[:36]).decode()
    if data_total > 36:
        data_str = data_str[:-2] + ".."
    text = Text("Confirm data", ui.ICON_SEND, ui.GREEN)
    text.bold("Size: %d bytes" % data_total)
    text.mono(*split_data(data_str))
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


def format_ethereum_amount(value: int, token, chain_id: int, tx_type=None):
    if token is tokens.UNKNOWN_TOKEN:
        suffix = "Wei UNKN"
        decimals = 0
    elif token:
        suffix = token[2]
        decimals = token[3]
    else:
        suffix = networks.shortcut_by_chain_id(chain_id, tx_type)
        decimals = 18

    # Don't want to display wei values for tokens with small decimal numbers
    if decimals > 9 and value < 10 ** (decimals - 9):
        suffix = "Wei " + suffix
        decimals = 0

    return "%s %s" % (format_amount(value, decimals), suffix)
