from trezor.crypto.hashlib import sha256
from trezor.messages import EosTxActionAck, EosTxActionRequest
from trezor.utils import HashWriter

from .. import helpers, writers
from . import layout

if False:
    from trezor import wire
    from trezor.utils import Writer


async def process_action(
    ctx: wire.Context, sha: HashWriter, action: EosTxActionAck
) -> None:
    name = helpers.eos_name_to_string(action.common.name)
    account = helpers.eos_name_to_string(action.common.account)

    if not check_action(action, name, account):
        raise ValueError("Invalid action")

    w = bytearray()
    if account == "eosio":
        if name == "buyram":
            await layout.confirm_action_buyram(ctx, action.buy_ram)
            writers.write_action_buyram(w, action.buy_ram)
        elif name == "buyrambytes":
            await layout.confirm_action_buyrambytes(ctx, action.buy_ram_bytes)
            writers.write_action_buyrambytes(w, action.buy_ram_bytes)
        elif name == "sellram":
            await layout.confirm_action_sellram(ctx, action.sell_ram)
            writers.write_action_sellram(w, action.sell_ram)
        elif name == "delegatebw":
            await layout.confirm_action_delegate(ctx, action.delegate)
            writers.write_action_delegate(w, action.delegate)
        elif name == "undelegatebw":
            await layout.confirm_action_undelegate(ctx, action.undelegate)
            writers.write_action_undelegate(w, action.undelegate)
        elif name == "refund":
            await layout.confirm_action_refund(ctx, action.refund)
            writers.write_action_refund(w, action.refund)
        elif name == "voteproducer":
            await layout.confirm_action_voteproducer(ctx, action.vote_producer)
            writers.write_action_voteproducer(w, action.vote_producer)
        elif name == "updateauth":
            await layout.confirm_action_updateauth(ctx, action.update_auth)
            writers.write_action_updateauth(w, action.update_auth)
        elif name == "deleteauth":
            await layout.confirm_action_deleteauth(ctx, action.delete_auth)
            writers.write_action_deleteauth(w, action.delete_auth)
        elif name == "linkauth":
            await layout.confirm_action_linkauth(ctx, action.link_auth)
            writers.write_action_linkauth(w, action.link_auth)
        elif name == "unlinkauth":
            await layout.confirm_action_unlinkauth(ctx, action.unlink_auth)
            writers.write_action_unlinkauth(w, action.unlink_auth)
        elif name == "newaccount":
            await layout.confirm_action_newaccount(ctx, action.new_account)
            writers.write_action_newaccount(w, action.new_account)
        else:
            raise ValueError("Unrecognized action type for eosio")
    elif name == "transfer":
        await layout.confirm_action_transfer(ctx, action.transfer, account)
        writers.write_action_transfer(w, action.transfer)
    else:
        await process_unknown_action(ctx, w, action)

    writers.write_action_common(sha, action.common)
    writers.write_bytes_prefixed(sha, w)


async def process_unknown_action(
    ctx: wire.Context, w: Writer, action: EosTxActionAck
) -> None:
    checksum = HashWriter(sha256())
    writers.write_uvarint(checksum, action.unknown.data_size)
    checksum.extend(action.unknown.data_chunk)

    writers.write_bytes_unchecked(w, action.unknown.data_chunk)
    bytes_left = action.unknown.data_size - len(action.unknown.data_chunk)

    while bytes_left != 0:
        action = await ctx.call(
            EosTxActionRequest(data_size=bytes_left), EosTxActionAck
        )

        if action.unknown is None:
            raise ValueError("Bad response. Unknown struct expected.")

        checksum.extend(action.unknown.data_chunk)
        writers.write_bytes_unchecked(w, action.unknown.data_chunk)

        bytes_left -= len(action.unknown.data_chunk)
        if bytes_left < 0:
            raise ValueError("Bad response. Buffer overflow.")

    await layout.confirm_action_unknown(ctx, action.common, checksum.get_digest())


def check_action(action: EosTxActionAck, name: str, account: str) -> bool:
    if account == "eosio":
        if (
            (name == "buyram" and action.buy_ram is not None)
            or (name == "buyrambytes" and action.buy_ram_bytes is not None)
            or (name == "sellram" and action.sell_ram is not None)
            or (name == "delegatebw" and action.delegate is not None)
            or (name == "undelegatebw" and action.undelegate is not None)
            or (name == "refund" and action.refund is not None)
            or (name == "voteproducer" and action.vote_producer is not None)
            or (name == "updateauth" and action.update_auth is not None)
            or (name == "deleteauth" and action.delete_auth is not None)
            or (name == "linkauth" and action.link_auth is not None)
            or (name == "unlinkauth" and action.unlink_auth is not None)
            or (name == "newaccount" and action.new_account is not None)
        ):
            return True
        else:
            return False

    elif name == "transfer":
        return action.transfer is not None

    elif action.unknown is not None:
        return True

    return False
