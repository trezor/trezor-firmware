from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_properties

from ..helpers import eos_asset_to_string, eos_name_to_string

if TYPE_CHECKING:
    from typing import Iterable

    from trezor.messages import (
        EosActionBuyRam,
        EosActionBuyRamBytes,
        EosActionCommon,
        EosActionDelegate,
        EosActionDeleteAuth,
        EosActionLinkAuth,
        EosActionNewAccount,
        EosActionRefund,
        EosActionSellRam,
        EosActionTransfer,
        EosActionUndelegate,
        EosActionUnlinkAuth,
        EosActionUpdateAuth,
        EosActionVoteProducer,
        EosAuthorization,
    )
    from trezor.ui.layouts import PropertyType


# Whether action is last - and should be HoldToConfirm
is_last = False


# Because icon and br_code are almost always the same
# (and also calling with positional arguments takes less space)
async def _confirm_properties(
    br_name: str,
    title: str,
    props: Iterable[PropertyType],
) -> None:
    await confirm_properties(
        br_name,
        title,
        props,
        hold=is_last,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_buyram(msg: EosActionBuyRam) -> None:
    await _confirm_properties(
        "confirm_buyram",
        TR.eos__buy_ram,
        (
            (TR.eos__payer, eos_name_to_string(msg.payer), True),
            (TR.eos__receiver, eos_name_to_string(msg.receiver), True),
            (f"{TR.words__amount}:", eos_asset_to_string(msg.quantity), True),
        ),
    )


async def confirm_action_buyrambytes(msg: EosActionBuyRamBytes) -> None:
    await _confirm_properties(
        "confirm_buyrambytes",
        TR.eos__buy_ram,
        (
            (TR.eos__payer, eos_name_to_string(msg.payer), True),
            (TR.eos__receiver, eos_name_to_string(msg.receiver), True),
            (TR.eos__bytes, str(msg.bytes), True),
        ),
    )


async def confirm_action_delegate(msg: EosActionDelegate) -> None:
    props: list[PropertyType] = [
        (TR.eos__sender, eos_name_to_string(msg.sender), True),
        (TR.eos__receiver, eos_name_to_string(msg.receiver), True),
        (TR.eos__cpu, eos_asset_to_string(msg.cpu_quantity), True),
        (TR.eos__net, eos_asset_to_string(msg.net_quantity), True),
    ]
    append = props.append  # local_cache_attribute
    if msg.transfer:
        append((TR.eos__transfer, TR.words__yes, False))
        append((TR.eos__receiver, eos_name_to_string(msg.receiver), True))
    else:
        append((TR.eos__transfer, TR.words__no, False))

    await _confirm_properties(
        "confirm_delegate",
        TR.eos__delegate,
        props,
    )


async def confirm_action_sellram(msg: EosActionSellRam) -> None:
    await _confirm_properties(
        "confirm_sellram",
        TR.eos__sell_ram,
        (
            (TR.eos__receiver, eos_name_to_string(msg.account), True),
            (TR.eos__bytes, str(msg.bytes), True),
        ),
    )


async def confirm_action_undelegate(msg: EosActionUndelegate) -> None:
    await _confirm_properties(
        "confirm_undelegate",
        TR.eos__undelegate,
        (
            (TR.eos__sender, eos_name_to_string(msg.sender), True),
            (TR.eos__receiver, eos_name_to_string(msg.receiver), True),
            (TR.eos__cpu, eos_asset_to_string(msg.cpu_quantity), True),
            (TR.eos__net, eos_asset_to_string(msg.net_quantity), True),
        ),
    )


async def confirm_action_refund(msg: EosActionRefund) -> None:
    await _confirm_properties(
        "confirm_refund",
        TR.eos__refund,
        ((TR.eos__owner, eos_name_to_string(msg.owner), True),),
    )


async def confirm_action_voteproducer(msg: EosActionVoteProducer) -> None:
    producers = msg.producers  # local_cache_attribute

    if msg.proxy and not producers:
        # PROXY
        await _confirm_properties(
            "confirm_voteproducer",
            TR.eos__vote_for_proxy,
            (
                (TR.eos__voter, eos_name_to_string(msg.voter), True),
                (TR.eos__proxy, eos_name_to_string(msg.proxy), True),
            ),
        )

    elif producers:
        # PRODUCERS
        await _confirm_properties(
            "confirm_voteproducer",
            TR.eos__vote_for_producers,
            (
                (f"{wi:2d}. {eos_name_to_string(producer)}", None, None)
                for wi, producer in enumerate(producers, 1)
            ),
        )

    else:
        # Cancel vote
        await _confirm_properties(
            "confirm_voteproducer",
            TR.eos__cancel_vote,
            ((TR.eos__voter, eos_name_to_string(msg.voter), True),),
        )


async def confirm_action_transfer(msg: EosActionTransfer, account: str) -> None:
    props = [
        (TR.eos__from, eos_name_to_string(msg.sender), True),
        (TR.eos__to, eos_name_to_string(msg.receiver), True),
        (f"{TR.words__amount}:", eos_asset_to_string(msg.quantity), True),
        (TR.eos__contract, account, True),
    ]
    if msg.memo is not None:
        props.append((TR.eos__memo, msg.memo[:512], True))
    await _confirm_properties(
        "confirm_transfer",
        TR.eos__transfer.replace(":", ""),
        props,
    )


async def confirm_action_updateauth(msg: EosActionUpdateAuth) -> None:
    props: list[PropertyType] = [
        (f"{TR.words__account}:", eos_name_to_string(msg.account), True),
        (TR.eos__permission, eos_name_to_string(msg.permission), True),
        (TR.eos__parent, eos_name_to_string(msg.parent), True),
    ]
    props.extend(authorization_fields(msg.auth))
    await _confirm_properties(
        "confirm_updateauth",
        TR.eos__update_auth,
        props,
    )


async def confirm_action_deleteauth(msg: EosActionDeleteAuth) -> None:
    await _confirm_properties(
        "confirm_deleteauth",
        TR.eos__delete_auth,
        (
            (f"{TR.words__account}:", eos_name_to_string(msg.account), True),
            (TR.eos__permission, eos_name_to_string(msg.permission), True),
        ),
    )


async def confirm_action_linkauth(msg: EosActionLinkAuth) -> None:
    await _confirm_properties(
        "confirm_linkauth",
        TR.eos__link_auth,
        (
            (f"{TR.words__account}:", eos_name_to_string(msg.account), True),
            (TR.eos__code, eos_name_to_string(msg.code), True),
            (TR.eos__type, eos_name_to_string(msg.type), True),
            (TR.eos__requirement, eos_name_to_string(msg.requirement), True),
        ),
    )


async def confirm_action_unlinkauth(msg: EosActionUnlinkAuth) -> None:
    await _confirm_properties(
        "confirm_unlinkauth",
        TR.eos__unlink_auth,
        (
            (f"{TR.words__account}:", eos_name_to_string(msg.account), True),
            (TR.eos__code, eos_name_to_string(msg.code), True),
            (TR.eos__type, eos_name_to_string(msg.type), True),
        ),
    )


async def confirm_action_newaccount(msg: EosActionNewAccount) -> None:
    props: list[PropertyType] = [
        (TR.eos__creator, eos_name_to_string(msg.creator), True),
        (TR.eos__name, eos_name_to_string(msg.name), True),
    ]
    props.extend(authorization_fields(msg.owner))
    props.extend(authorization_fields(msg.active))
    await _confirm_properties(
        "confirm_newaccount",
        TR.eos__new_account,
        props,
    )


async def confirm_action_unknown(action: EosActionCommon, checksum: bytes) -> None:
    await confirm_properties(
        "confirm_unknown",
        TR.eos__arbitrary_data,
        (
            (TR.eos__contract, eos_name_to_string(action.account), False),
            (TR.eos__action_name, eos_name_to_string(action.name), False),
            (TR.eos__checksum, checksum, True),
        ),
        hold=is_last,
        br_code=ButtonRequestType.ConfirmOutput,
    )


def authorization_fields(auth: EosAuthorization) -> list[PropertyType]:
    from trezor.wire import DataError

    from ..helpers import public_key_to_wif

    fields: list[PropertyType] = []
    append = fields.append  # local_cache_attribute

    append((TR.eos__threshold, str(auth.threshold), False))

    # NOTE: getting rid of f-strings saved almost 100 bytes

    for i, key in enumerate(auth.keys, 1):
        if key.key is None:
            raise DataError("Key must be provided explicitly.")

        _key = public_key_to_wif(bytes(key.key))
        _weight = str(key.weight)

        header = f"Key #{i}:"
        w_header = f"Key #{i} Weight:"

        append((header, _key, True))
        append((w_header, _weight, True))

    for i, account in enumerate(auth.accounts, 1):
        _account = eos_name_to_string(account.account.actor)
        _permission = eos_name_to_string(account.account.permission)

        i = str(i)
        # TODO: handle translation
        a_header = f"Account #{i}:"
        p_header = f"Acc Permission #{i}:"
        w_header = f"Account #{i} weight:"

        append((a_header, _account, True))
        append((p_header, _permission, True))
        append((w_header, str(account.weight), True))

    for i, wait in enumerate(auth.waits, 1):
        _wait = str(wait.wait_sec)
        _weight = str(wait.weight)

        header = f"Delay #{i}"
        w_header = f"{header} weight:"
        append((f"{header}:", _wait + " sec", False))
        append((w_header, _weight, False))

    return fields
