from ubinascii import unhexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.RippleIssuedAmount import RippleIssuedAmount
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount
from trezor.wire import ProcessError

from . import definitions, helpers

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.common.layout import split_address


def add_page_numbers(pages):
    for i, page in enumerate(pages):
        page.header_text = page.header_text + " %s/%s" % (i + 1, len(pages))
    return pages


def time_text(title: str, description: str, timestamp: int):
    text = Text(title, ui.ICON_SEND, ui.GREEN)
    text.normal(description)
    time = helpers.time_from_ripple_timestamp(timestamp)
    text.bold("%04d-%02d-%02d" % time[:3])
    text.bold("%02d:%02d:%02d" % time[3:6])
    return text


def flags_text(title: str, transaction_type: str, flags: int):
    text = Text(title, ui.ICON_SEND, ui.GREEN)
    text.normal("Flags:")
    flags_list = []
    for value in definitions.FLAGS[transaction_type]:
        if flags & value == value:
            flags_list.append(definitions.FLAGS[transaction_type][value])
    if not flags_list:
        return None
    text.mono_bold(*flags_list)
    return text


def is_standard_currency(currency):
    return len(currency) == 3


def remove_currency_suffix(currency):
    while currency.endswith("00"):
        currency = currency[:-2]

    return currency


def is_decodable_currency(currency_bytes):
    # Don't allow empty currencies
    if len(currency_bytes) == 0:
        return False

    for b in currency_bytes:
        # Don't allow non-printable currencies
        if b < 32 or b > 126:
            return False

    return True


def decode_currency(currency):
    if is_standard_currency(currency):
        return currency
    else:
        without_padding = remove_currency_suffix(currency)
        currency_bytes = unhexlify(without_padding)

        if is_decodable_currency(currency_bytes):
            try:
                return currency_bytes.decode("ascii")
            except ValueError:
                return currency
        else:
            return currency


def main_page_content(amount: RippleIssuedAmount):
    if amount.value:
        if is_standard_currency(amount.currency):
            return amount.currency + " " + amount.value
        else:
            return amount.value
    else:
        return decode_currency(amount.currency)


def issued_amount_text(title: str, type: str, amount: RippleIssuedAmount):
    pages = []

    main_page = Text(title, ui.ICON_SEND, ui.GREEN)
    main_page.normal(type)
    main_page.bold(*chunks(main_page_content(amount), 17))
    pages.append(main_page)

    if amount.value and not is_standard_currency(amount.currency):
        currency_page = Text(title, ui.ICON_SEND, ui.GREEN)
        currency_page.normal("Currency:")
        currency_page.bold(*chunks(decode_currency(amount.currency), 17))
        pages.append(currency_page)

    if amount.issuer:
        issuer_page = Text(title, ui.ICON_SEND, ui.GREEN)
        issuer_page.normal("Issuer:")
        issuer_page.mono_bold(*split_address(amount.issuer))
        pages.append(issuer_page)

    return pages


def xrp_destination_text(amount, destination, title, amount_type="Amount:"):
    amount_page = standard_field_text(
        title, amount_type, "XRP " + format_amount(amount, definitions.DIVISIBILITY)
    )

    destination_page = standard_field_text(
        title, "Destination:", destination, address=True
    )

    return (amount_page, destination_page)


def standard_field_text(
    title: str,
    field_description: str,
    value: str,
    mono=False,
    shorten=False,
    address=False,
):
    text = Text(title, ui.ICON_SEND, ui.GREEN)
    text.normal(field_description)
    if mono:
        if shorten:
            text.mono_bold(*shorten_to_fit(value, 17 * 4))
        elif address:
            text.mono_bold(*split_address(value))
        else:
            text.mono_bold(*chunks(value, 17))
    else:
        if shorten:
            text.bold(*shorten_to_fit(value, 17 * 4))
        elif address:
            text.bold(*split_address(value))
        else:
            text.bold(*chunks(value, 17))
    return text


def shorten_to_fit(string: str, desired_length: int):
    if len(string) > desired_length:
        return chunks(
            "{0}....{1}".format(
                string[: (desired_length - 4) // 2],
                string[-(desired_length - 4) // 2 :],
            ),
            17,
        )
    else:
        return chunks(string, 17)


async def require_hold_to_confirm_for_pages(ctx, pages):
    pages = list(filter(None, pages))
    if len(pages) == 1:
        return await require_hold_to_confirm(ctx, pages[0], ButtonRequestType.SignTx)
    else:
        pages = add_page_numbers(pages)
        paginated = Paginated(pages)
        return await require_hold_to_confirm(ctx, paginated, ButtonRequestType.SignTx)


async def require_confirm_for_pages(ctx, pages):
    pages = list(filter(None, pages))
    if len(pages) == 1:
        return await require_confirm(ctx, pages[0], ButtonRequestType.SignTx)
    else:
        pages = add_page_numbers(pages)
        paginated = Paginated(pages)
        return await require_confirm(ctx, paginated, ButtonRequestType.SignTx)


async def require_confirm_common(
    ctx, source_address, fee, account_txn_id, memos, signers, source_tag
):
    title = "Common"
    pages = []

    pages.append(
        standard_field_text(title, "Account:", source_address, mono=True, shorten=True)
    )

    pages.append(
        standard_field_text(
            title, "Fee:", "XRP " + format_amount(fee, definitions.DIVISIBILITY)
        )
    )

    if account_txn_id:
        pages.append(standard_field_text(title, "Account Txn ID:", account_txn_id))

    if memos:
        for i, memo in enumerate(memos):
            if memo.memo.memo_format:
                try:
                    pages.append(
                        standard_field_text(
                            title,
                            "Memo Format {0}/{1}:".format(i + 1, len(memos)),
                            unhexlify(memo.memo.memo_format).decode("ascii"),
                            mono=True,
                            shorten=True,
                        )
                    )
                except (UnicodeError, ValueError):
                    # https://xrpl.org/transaction-common-fields.html#memos-field
                    raise ProcessError(
                        "Only characters allowed in URLs accepted as memo format"
                    )
            if memo.memo.memo_type:
                try:
                    pages.append(
                        standard_field_text(
                            title,
                            "Memo Type {0}/{1}:".format(i + 1, len(memos)),
                            unhexlify(memo.memo.memo_type).decode("ascii"),
                            mono=True,
                            shorten=True,
                        )
                    )
                except (UnicodeError, ValueError):
                    # https://xrpl.org/transaction-common-fields.html#memos-field
                    raise ProcessError(
                        "Only characters allowed in URLs accepted as memo type"
                    )
            if memo.memo.memo_data:
                try:
                    pages.append(
                        standard_field_text(
                            title,
                            "Memo Data {0}/{1}:".format(i + 1, len(memos)),
                            unhexlify(memo.memo.memo_data).decode("ascii"),
                            mono=True,
                            shorten=True,
                        )
                    )

                except (UnicodeError, ValueError):
                    pages.append(
                        standard_field_text(
                            title,
                            "Memo Data (hex) {0}/{1}:".format(i + 1, len(memos)),
                            memo.memo.memo_data,
                            mono=True,
                            shorten=True,
                        )
                    )

    if signers:
        for i, signer in enumerate(signers):
            if signer.signer.account:
                pages.append(
                    standard_field_text(
                        title,
                        "Signer Account {0}/{1}:".format(i + 1, len(signers)),
                        signer.signer.account,
                        mono=True,
                        shorten=True,
                    )
                )
            if signer.signer.txn_signature:
                pages.append(
                    standard_field_text(
                        title,
                        "Signer Txn Sig. {0}/{1}:".format(i + 1, len(signers)),
                        signer.signer.txn_signature,
                        mono=True,
                        shorten=True,
                    )
                )
            if signer.signer.signing_pub_key:
                pages.append(
                    standard_field_text(
                        title,
                        "Signer Sig.PubKey {0}/{1}:".format(i + 1, len(signers)),
                        signer.signer.signing_pub_key,
                        mono=True,
                        shorten=True,
                    )
                )

    if source_tag:
        pages.append(standard_field_text(title, "Source Tag:", str(source_tag)))
    return await require_confirm_for_pages(ctx, pages)


async def require_confirm_regular_key(ctx, regular_key):
    text = standard_field_text("Set Regular Key", "Regular Key:", str(regular_key))

    return await require_hold_to_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_escrow_cancel(ctx, owner: str, offer_sequence: int):
    title = "Cancel Escrow"
    pages = []

    pages.append(standard_field_text(title, "Owner:", owner, mono=True, address=True))
    pages.append(standard_field_text(title, "Offer Sequence:", str(offer_sequence)))

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_escrow_create(
    ctx,
    amount,
    destination,
    cancel_after=None,
    finish_after=None,
    condition=None,
    destination_tag=None,
):
    title = "Create Escrow"
    pages = []

    pages.extend(xrp_destination_text(amount, destination, title))

    if cancel_after is not None:
        pages.append(time_text(title, "Cancel After:", cancel_after))

    if finish_after is not None:
        pages.append(time_text(title, "Finish After:", finish_after))

    if condition is not None:
        pages.append(
            standard_field_text(title, "Condition:", condition, mono=True, shorten=True)
        )

    if destination_tag is not None:
        pages.append(
            standard_field_text(title, "Destination Tag:", str(destination_tag))
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_escrow_finish(
    ctx, owner, offer_sequence, condition=None, fulfillment=None
):
    title = "Finish Escrow"
    pages = []

    pages.append(standard_field_text(title, "Owner:", owner, mono=True, address=True))
    pages.append(standard_field_text(title, "Offer Sequence:", str(offer_sequence)))

    if condition is not None:
        pages.append(
            standard_field_text(title, "Condition:", condition, mono=True, shorten=True)
        )

    if fulfillment is not None:
        pages.append(
            standard_field_text(
                title, "Fulfillment:", fulfillment, mono=True, shorten=True
            )
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_account_set(
    ctx,
    flags,
    clear_flag=None,
    set_flag=None,
    domain=None,
    email_hash=None,
    message_key=None,
    transfer_rate=None,
    tick_size=None,
):
    title = "Account Set"
    pages = []
    pages.append(flags_text(title, "account_set", flags))

    if clear_flag is not None:
        pages.append(
            standard_field_text(
                title,
                "Clear Flag:",
                definitions.FLAGS["account_set"][clear_flag],
                mono=True,
            )
        )

    if domain is not None:
        pages.append(
            standard_field_text(
                title, "Domain:", unhexlify(domain), mono=True, shorten=True
            )
        )

    if email_hash is not None:
        pages.append(
            standard_field_text(
                title, "Email Hash:", email_hash, mono=True, shorten=True
            )
        )

    if message_key is not None:
        pages.append(
            standard_field_text(
                title, "Message Key:", message_key, mono=True, shorten=True
            )
        )

    if transfer_rate is not None:
        if transfer_rate == 0:
            pages.append(standard_field_text(title, "Transfer Rate:", "0 %", mono=True))
        else:
            pages.append(
                standard_field_text(
                    title,
                    "Transfer Rate:",
                    "{0}.{1:07d} %".format(
                        (transfer_rate - 1000000000) // 10000000,
                        transfer_rate % 10000000,
                    ),
                    mono=True,
                )
            )

    if set_flag is not None:
        pages.append(
            standard_field_text(
                title,
                "Set Flag:",
                definitions.FLAGS["account_set"][set_flag],
                mono=True,
            )
        )

    if tick_size is not None:
        pages.append(
            standard_field_text(title, "Tick Size:", str(tick_size), mono=True)
        )

    if len(list(filter(None, pages))) == 0:
        pages.append(standard_field_text(title, "Empty", ""))

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_payment_channel_create(
    ctx,
    amount,
    destination,
    settle_delay,
    public_key,
    cancel_after=None,
    destination_tag=None,
):
    title = "Create Channel"
    pages = []

    pages.extend(xrp_destination_text(amount, destination, title))

    pages.append(
        standard_field_text(title, "Settle Delay:", "{0} s".format(settle_delay))
    )

    pages.append(
        standard_field_text(title, "Public Key:", public_key, mono=True, shorten=True)
    )

    if cancel_after is not None:
        pages.append(time_text(title, "Cancel After:", cancel_after))

    if destination_tag is not None:
        pages.append(
            standard_field_text(title, "Destination Tag:", str(destination_tag))
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_payment_channel_fund(ctx, amount, channel, expiration=None):
    title = "Fund Channel"
    pages = []

    pages.append(
        standard_field_text(title, "Channel:", channel, mono=True, shorten=True)
    )

    pages.append(
        standard_field_text(
            title,
            "Amount:",
            "XRP " + format_amount(amount, definitions.DIVISIBILITY),
            mono=True,
            shorten=True,
        )
    )

    if expiration is not None:
        pages.append(time_text(title, "Expiration:", expiration))

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_payment_channel_claim(
    ctx, flags, channel, balance=None, amount=None, signature=None, public_key=None
):
    title = "Channel Claim"
    pages = []

    pages.append(flags_text(title, "payment_channel_claim", flags))
    pages.append(
        standard_field_text(title, "Channel:", channel, mono=True, shorten=True)
    )

    if balance is not None:
        pages.append(
            standard_field_text(
                title,
                "Balance:",
                "XRP " + format_amount(balance, definitions.DIVISIBILITY),
                mono=True,
            )
        )

    if amount is not None:
        pages.append(
            standard_field_text(
                title,
                "Amount:",
                "XRP " + format_amount(amount, definitions.DIVISIBILITY),
                mono=True,
            )
        )

    if signature is not None:
        pages.append(
            standard_field_text(title, "Signature:", signature, mono=True, shorten=True)
        )

    if public_key is not None:
        pages.append(
            standard_field_text(
                title, "Public Key:", public_key, mono=True, shorten=True
            )
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_trust_set(
    ctx, flags, limit_amount, quality_in=None, quality_out=None
):
    title = "Set Trust Line"
    pages = []

    pages.append(flags_text(title, "trust_set", flags))
    pages.extend(issued_amount_text(title, "Limit Amount:", limit_amount))

    if quality_in is not None:
        if quality_in == 0:
            pages.append(standard_field_text(title, "Quality In:", "100 %", mono=True))
        else:
            pages.append(
                standard_field_text(
                    title,
                    "Quality In:",
                    "{0}.{1:07d} %".format(
                        quality_in // 10000000, quality_in % 10000000
                    ),
                    mono=True,
                )
            )

    if quality_out is not None:
        if quality_out == 0:
            pages.append(standard_field_text(title, "Quality Out:", "100 %", mono=True))
        else:
            pages.append(
                standard_field_text(
                    title,
                    "Quality Out:",
                    "{0}.{1:07d} %".format(
                        quality_out // 10000000, quality_out % 10000000
                    ),
                    mono=True,
                )
            )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_payment(
    ctx,
    flags,
    amount,
    destination,
    issued_amount: RippleIssuedAmount,
    destination_tag,
    paths,
    invoice_id,
    send_max,
    issued_send_max,
    deliver_min,
    issued_deliver_min,
):
    title = "Payment"
    pages = []

    if issued_amount is not None:
        pages.extend(issued_amount_text(title, "Amount:", issued_amount))
        text = Text(title, ui.ICON_SEND, ui.GREEN)
        text.normal("Destination:")
        text.mono_bold(*split_address(destination))
        pages.append(text)
    else:
        pages.extend(xrp_destination_text(amount, destination, title))

    if destination_tag is not None:
        pages.append(
            standard_field_text(
                title, "Destination Tag:", str(destination_tag), mono=True
            )
        )

    if paths:
        for path_idx, path in enumerate(paths):
            for step_idx, step in enumerate(path.path):
                if step.account:
                    text = Text(title, ui.ICON_SEND, ui.GREEN)
                    text.normal(
                        "Path {0}/{1}, step {2}/{3}".format(
                            path_idx + 1, len(paths), step_idx + 1, len(path.path)
                        )
                    )
                    text.normal("Account:")
                    text.mono_bold(*split_address(step.account))
                    pages.append(text)
                if step.currency:
                    text = Text(title, ui.ICON_SEND, ui.GREEN)
                    text.normal(
                        "Path {0}/{1}, step {2}/{3}".format(
                            path_idx + 1, len(paths), step_idx + 1, len(path.path)
                        )
                    )
                    text.normal("Currency:")
                    text.mono_bold(*chunks(decode_currency(step.currency), 17))
                    pages.append(text)
                if step.issuer:
                    text = Text(title, ui.ICON_SEND, ui.GREEN)
                    text.normal(
                        "Path {0}/{1}, step {2}/{3}".format(
                            path_idx + 1, len(paths), step_idx + 1, len(path.path)
                        )
                    )
                    text.normal("Issuer:")
                    text.mono_bold(*split_address(step.issuer))
                    pages.append(text)

    if invoice_id is not None:
        pages.append(
            standard_field_text(
                title, "Invoice ID:", invoice_id, mono=True, shorten=True
            )
        )

    if send_max is not None:
        pages.append(
            standard_field_text(
                title,
                "Send Max:",
                "XRP " + format_amount(send_max, definitions.DIVISIBILITY),
            )
        )

    elif issued_send_max is not None:
        pages.extend(issued_amount_text(title, "Send Max:", issued_send_max))

    if deliver_min is not None:
        pages.append(
            standard_field_text(
                title,
                "Deliver Min:",
                "XRP " + format_amount(deliver_min, definitions.DIVISIBILITY),
            )
        )

    elif issued_deliver_min is not None:
        pages.extend(issued_amount_text(title, "Deliver Min:", issued_deliver_min))

    pages.append(flags_text(title, "payment", flags))

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_offer_create(
    ctx,
    flags,
    expiration,
    offer_sequence,
    taker_gets,
    issued_taker_gets,
    taker_pays,
    issued_taker_pays,
):
    title = "Create Offer"
    pages = []

    if offer_sequence:
        pages.append(standard_field_text(title, "Offer Sequence:", str(offer_sequence)))

    if issued_taker_pays:
        pages.extend(issued_amount_text(title, "Taker Pays:", issued_taker_pays))
    else:
        pages.append(
            standard_field_text(
                title,
                "Taker Pays:",
                "XRP " + format_amount(taker_pays, definitions.DIVISIBILITY),
            )
        )

    if issued_taker_gets is not None:
        pages.extend(issued_amount_text(title, "Taker Gets:", issued_taker_gets))
    else:
        pages.append(
            standard_field_text(
                title,
                "Taker Gets:",
                "XRP " + format_amount(taker_gets, definitions.DIVISIBILITY),
            )
        )

    if expiration:
        pages.append(time_text(title, "Expiration:", expiration))

    pages.append(flags_text(title, "offer_create", flags))

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_offer_cancel(ctx, offer_sequence):
    text = standard_field_text(
        "Cancel Offer", "Offer Sequence:", str(offer_sequence), mono=True
    )
    return await require_hold_to_confirm(ctx, text)


async def require_confirm_signer_list_set(ctx, signer_quorum, signer_entries):
    title = "Set Signer List"
    pages = []

    pages.append(standard_field_text(title, "Quorum:", str(signer_quorum)))

    for i, entry in enumerate(signer_entries):
        text = Text(title, ui.ICON_SEND, ui.GREEN)
        text.normal("Signer Account {0}/{1}:".format(i + 1, len(signer_entries)))
        text.mono_bold(*split_address(entry.signer_entry.account))
        pages.append(text)
        text = Text(title, ui.ICON_SEND, ui.GREEN)
        text.normal("Signer Weight {0}/{1}:".format(i + 1, len(signer_entries)))
        text.bold(str(entry.signer_entry.signer_weight))
        pages.append(text)
    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_check_create(
    ctx, destination, send_max, issued_send_max, destination_tag, expiration, invoice_id
):
    title = "Create Check"
    pages = []

    if issued_send_max is not None:
        pages.extend(issued_amount_text(title, "Send Max:", issued_send_max))
        text = Text(title, ui.ICON_SEND, ui.GREEN)
        text.normal("Destination:")
        text.mono_bold(*split_address(destination))
        pages.append(text)
    else:
        pages.extend(
            xrp_destination_text(send_max, destination, title, amount_type="Send Max:")
        )

    if expiration is not None:
        pages.append(time_text(title, "Expiration:", expiration))

    if invoice_id is not None:
        pages.append(
            standard_field_text(
                title, "Invoice ID:", invoice_id, mono=True, shorten=True
            )
        )

    if destination_tag is not None:
        pages.append(
            standard_field_text(title, "Destination Tag:", str(destination_tag))
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_check_cancel(ctx, check_id):
    text = Text("Cancel Check", ui.ICON_SEND, ui.GREEN)
    text.normal("Check ID:")
    text.mono_bold(*chunks(check_id, 17))

    return await require_hold_to_confirm(ctx, text)


async def require_confirm_check_cash(
    ctx, check_id, amount, issued_amount, deliver_min, issued_deliver_min
):
    title = "Cash Check"
    pages = []

    text = Text(title, ui.ICON_SEND, ui.GREEN)
    text.normal("Check ID:")
    text.mono(*chunks(check_id, 17))
    pages.append(text)

    if issued_amount is not None:
        pages.extend(issued_amount_text(title, "Amount:", issued_amount))
    elif amount is not None:
        pages.append(
            standard_field_text(
                title,
                "Amount:",
                "XRP " + format_amount(amount, definitions.DIVISIBILITY),
            )
        )
    elif issued_deliver_min is not None:
        pages.extend(issued_amount_text(title, "Deliver Min:", issued_amount))
    elif deliver_min is not None:
        pages.append(
            standard_field_text(
                title,
                "Deliver Min:",
                "XRP " + format_amount(deliver_min, definitions.DIVISIBILITY),
            )
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)


async def require_confirm_deposit_preauth(ctx, authorize, unauthorize):
    title = "Preauth. Deposit"
    if authorize:
        text = standard_field_text(
            title, "Authorize:", authorize, mono=True, address=True
        )

        return await require_hold_to_confirm(ctx, text)

    elif unauthorize:
        text = standard_field_text(
            title, "Unauthorize:", unauthorize, mono=True, address=True
        )

        return await require_hold_to_confirm(ctx, text)


async def require_get_public_key(ctx, public_key: str):
    text = Text("Confirm Public Key", ui.ICON_RECEIVE, ui.GREEN)
    text.mono_bold(*chunks(public_key, 17))
    await require_confirm(ctx, text, ButtonRequestType.PublicKey)


async def require_confirm_account_delete(ctx, destination, destination_tag=None):
    title = "Delete Account"
    pages = []

    pages.append(
        standard_field_text(title, "Destination", destination, mono=True, address=True)
    )

    if destination_tag is not None:
        pages.append(
            standard_field_text(title, "Destination Tag:", str(destination_tag))
        )

    return await require_hold_to_confirm_for_pages(ctx, pages)
