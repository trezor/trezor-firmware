from typing import TYPE_CHECKING

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
    br_type: str,
    title: str,
    props: Iterable[PropertyType],
) -> None:
    await confirm_properties(
        br_type,
        title,
        props,
        hold=is_last,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_action_buyram(msg: EosActionBuyRam) -> None:
    await _confirm_properties(
        "confirm_buyram",
        "Buy RAM",
        (
            ("Payer:", eos_name_to_string(msg.payer)),
            ("Receiver:", eos_name_to_string(msg.receiver)),
            ("Amount:", eos_asset_to_string(msg.quantity)),
        ),
    )


async def confirm_action_buyrambytes(msg: EosActionBuyRamBytes) -> None:
    await _confirm_properties(
        "confirm_buyrambytes",
        "Buy RAM",
        (
            ("Payer:", eos_name_to_string(msg.payer)),
            ("Receiver:", eos_name_to_string(msg.receiver)),
            ("Bytes:", str(msg.bytes)),
        ),
    )


async def confirm_action_delegate(msg: EosActionDelegate) -> None:
    props = [
        ("Sender:", eos_name_to_string(msg.sender)),
        ("Receiver:", eos_name_to_string(msg.receiver)),
        ("CPU:", eos_asset_to_string(msg.cpu_quantity)),
        ("NET:", eos_asset_to_string(msg.net_quantity)),
    ]
    append = props.append  # local_cache_attribute
    if msg.transfer:
        append(("Transfer:", "Yes"))
        append(("Receiver:", eos_name_to_string(msg.receiver)))
    else:
        append(("Transfer:", "No"))

    await _confirm_properties(
        "confirm_delegate",
        "Delegate",
        props,
    )


async def confirm_action_sellram(msg: EosActionSellRam) -> None:
    await _confirm_properties(
        "confirm_sellram",
        "Sell RAM",
        (
            ("Receiver:", eos_name_to_string(msg.account)),
            ("Bytes:", str(msg.bytes)),
        ),
    )


async def confirm_action_undelegate(msg: EosActionUndelegate) -> None:
    await _confirm_properties(
        "confirm_undelegate",
        "Undelegate",
        (
            ("Sender:", eos_name_to_string(msg.sender)),
            ("Receiver:", eos_name_to_string(msg.receiver)),
            ("CPU:", eos_asset_to_string(msg.cpu_quantity)),
            ("NET:", eos_asset_to_string(msg.net_quantity)),
        ),
    )


async def confirm_action_refund(msg: EosActionRefund) -> None:
    await _confirm_properties(
        "confirm_refund",
        "Refund",
        (("Owner:", eos_name_to_string(msg.owner)),),
    )


async def confirm_action_voteproducer(msg: EosActionVoteProducer) -> None:
    producers = msg.producers  # local_cache_attribute

    if msg.proxy and not producers:
        # PROXY
        await _confirm_properties(
            "confirm_voteproducer",
            "Vote for proxy",
            (
                ("Voter:", eos_name_to_string(msg.voter)),
                ("Proxy:", eos_name_to_string(msg.proxy)),
            ),
        )

    elif producers:
        # PRODUCERS
        await _confirm_properties(
            "confirm_voteproducer",
            "Vote for producers",
            (
                (f"{wi:2d}. {eos_name_to_string(producer)}", None)
                for wi, producer in enumerate(producers, 1)
            ),
        )

    else:
        # Cancel vote
        await _confirm_properties(
            "confirm_voteproducer",
            "Cancel vote",
            (("Voter:", eos_name_to_string(msg.voter)),),
        )


async def confirm_action_transfer(msg: EosActionTransfer, account: str) -> None:
    props = [
        ("From:", eos_name_to_string(msg.sender)),
        ("To:", eos_name_to_string(msg.receiver)),
        ("Amount:", eos_asset_to_string(msg.quantity)),
        ("Contract:", account),
    ]
    if msg.memo is not None:
        props.append(("Memo", msg.memo[:512]))
    await _confirm_properties(
        "confirm_transfer",
        "Transfer",
        props,
    )


async def confirm_action_updateauth(msg: EosActionUpdateAuth) -> None:
    props: list[PropertyType] = [
        ("Account:", eos_name_to_string(msg.account)),
        ("Permission:", eos_name_to_string(msg.permission)),
        ("Parent:", eos_name_to_string(msg.parent)),
    ]
    props.extend(authorization_fields(msg.auth))
    await _confirm_properties(
        "confirm_updateauth",
        "Update Auth",
        props,
    )


async def confirm_action_deleteauth(msg: EosActionDeleteAuth) -> None:
    await _confirm_properties(
        "confirm_deleteauth",
        "Delete Auth",
        (
            ("Account:", eos_name_to_string(msg.account)),
            ("Permission:", eos_name_to_string(msg.permission)),
        ),
    )


async def confirm_action_linkauth(msg: EosActionLinkAuth) -> None:
    await _confirm_properties(
        "confirm_linkauth",
        "Link Auth",
        (
            ("Account:", eos_name_to_string(msg.account)),
            ("Code:", eos_name_to_string(msg.code)),
            ("Type:", eos_name_to_string(msg.type)),
            ("Requirement:", eos_name_to_string(msg.requirement)),
        ),
    )


async def confirm_action_unlinkauth(msg: EosActionUnlinkAuth) -> None:
    await _confirm_properties(
        "confirm_unlinkauth",
        "Unlink Auth",
        (
            ("Account:", eos_name_to_string(msg.account)),
            ("Code:", eos_name_to_string(msg.code)),
            ("Type:", eos_name_to_string(msg.type)),
        ),
    )


async def confirm_action_newaccount(msg: EosActionNewAccount) -> None:
    props: list[PropertyType] = [
        ("Creator:", eos_name_to_string(msg.creator)),
        ("Name:", eos_name_to_string(msg.name)),
    ]
    props.extend(authorization_fields(msg.owner))
    props.extend(authorization_fields(msg.active))
    await _confirm_properties(
        "confirm_newaccount",
        "New Account",
        props,
    )


async def confirm_action_unknown(action: EosActionCommon, checksum: bytes) -> None:
    await confirm_properties(
        "confirm_unknown",
        "Arbitrary data",
        (
            ("Contract:", eos_name_to_string(action.account)),
            ("Action Name:", eos_name_to_string(action.name)),
            ("Checksum:", checksum),
        ),
        hold=is_last,
        br_code=ButtonRequestType.ConfirmOutput,
    )


def authorization_fields(auth: EosAuthorization) -> list[PropertyType]:
    from trezor.wire import DataError

    from ..helpers import public_key_to_wif

    fields: list[PropertyType] = []
    append = fields.append  # local_cache_attribute

    append(("Threshold:", str(auth.threshold)))

    # NOTE: getting rid of f-strings saved almost 100 bytes

    for i, key in enumerate(auth.keys, 1):
        if key.key is None:
            raise DataError("Key must be provided explicitly.")

        _key = public_key_to_wif(bytes(key.key))
        _weight = str(key.weight)

        header = "Key #" + str(i) + ":"
        w_header = "Key #" + str(i) + " Weight:"

        append((header, _key))
        append((w_header, _weight))

    for i, account in enumerate(auth.accounts, 1):
        _account = eos_name_to_string(account.account.actor)
        _permission = eos_name_to_string(account.account.permission)

        i = str(i)
        a_header = "Account #" + i + ":"
        p_header = "Acc Permission #" + i + ":"
        w_header = "Account #" + i + " weight:"

        append((a_header, _account))
        append((p_header, _permission))
        append((w_header, str(account.weight)))

    for i, wait in enumerate(auth.waits, 1):
        _wait = str(wait.wait_sec)
        _weight = str(wait.weight)

        header = "Delay #" + str(i)
        w_header = header + " weight:"
        append((header, _wait + " sec"))
        append((w_header, _weight))

    return fields
