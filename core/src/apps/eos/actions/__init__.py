from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EosTxActionAck
    from trezor.utils import HashWriter, Writer


async def process_action(
    sha: HashWriter, action: EosTxActionAck, is_last: bool
) -> None:
    from .. import helpers, writers
    from . import layout

    name = helpers.eos_name_to_string(action.common.name)
    account = helpers.eos_name_to_string(action.common.account)

    if not _check_action(action, name, account):
        raise ValueError("Invalid action")

    # Little cheat, not having to create "is_last" argument for every action layout
    # (not worth spending so many bytes in flash on this)
    layout.is_last = is_last

    w = bytearray()
    if account == "eosio":
        if name == "buyram":
            assert action.buy_ram is not None  # _check_action
            await layout.confirm_action_buyram(action.buy_ram)
            writers.write_action_buyram(w, action.buy_ram)
        elif name == "buyrambytes":
            assert action.buy_ram_bytes is not None  # _check_action
            await layout.confirm_action_buyrambytes(action.buy_ram_bytes)
            writers.write_action_buyrambytes(w, action.buy_ram_bytes)
        elif name == "sellram":
            assert action.sell_ram is not None  # _check_action
            await layout.confirm_action_sellram(action.sell_ram)
            writers.write_action_sellram(w, action.sell_ram)
        elif name == "delegatebw":
            assert action.delegate is not None  # _check_action
            await layout.confirm_action_delegate(action.delegate)
            writers.write_action_delegate(w, action.delegate)
        elif name == "undelegatebw":
            assert action.undelegate is not None  # _check_action
            await layout.confirm_action_undelegate(action.undelegate)
            writers.write_action_undelegate(w, action.undelegate)
        elif name == "refund":
            assert action.refund is not None  # _check_action
            await layout.confirm_action_refund(action.refund)
            writers.write_action_refund(w, action.refund)
        elif name == "voteproducer":
            assert action.vote_producer is not None  # _check_action
            await layout.confirm_action_voteproducer(action.vote_producer)
            writers.write_action_voteproducer(w, action.vote_producer)
        elif name == "updateauth":
            assert action.update_auth is not None  # _check_action
            await layout.confirm_action_updateauth(action.update_auth)
            writers.write_action_updateauth(w, action.update_auth)
        elif name == "deleteauth":
            assert action.delete_auth is not None  # _check_action
            await layout.confirm_action_deleteauth(action.delete_auth)
            writers.write_action_deleteauth(w, action.delete_auth)
        elif name == "linkauth":
            assert action.link_auth is not None  # _check_action
            await layout.confirm_action_linkauth(action.link_auth)
            writers.write_action_linkauth(w, action.link_auth)
        elif name == "unlinkauth":
            assert action.unlink_auth is not None  # _check_action
            await layout.confirm_action_unlinkauth(action.unlink_auth)
            writers.write_action_unlinkauth(w, action.unlink_auth)
        elif name == "newaccount":
            assert action.new_account is not None  # _check_action
            await layout.confirm_action_newaccount(action.new_account)
            writers.write_action_newaccount(w, action.new_account)
        else:
            raise ValueError("Unrecognized action type for eosio")
    elif name == "transfer":
        assert action.transfer is not None  # _check_action
        await layout.confirm_action_transfer(action.transfer, account)
        writers.write_action_transfer(w, action.transfer)
    else:
        await _process_unknown_action(w, action)

    writers.write_action_common(sha, action.common)
    writers.write_bytes_prefixed(sha, w)


async def _process_unknown_action(w: Writer, action: EosTxActionAck) -> None:
    from trezor.crypto.hashlib import sha256
    from trezor.messages import EosTxActionAck, EosTxActionRequest
    from trezor.utils import HashWriter
    from trezor.wire.context import call

    from .. import writers
    from . import layout

    unknown = action.unknown  # local_cache_attribute
    assert unknown is not None
    data_chunk = unknown.data_chunk  # local_cache_attribute

    checksum = HashWriter(sha256())
    writers.write_uvarint(checksum, unknown.data_size)
    checksum.extend(data_chunk)

    writers.write_bytes_unchecked(w, data_chunk)
    bytes_left = unknown.data_size - len(data_chunk)

    while bytes_left != 0:
        action = await call(EosTxActionRequest(data_size=bytes_left), EosTxActionAck)

        if unknown is None:
            raise ValueError("Bad response. Unknown struct expected.")

        checksum.extend(data_chunk)
        writers.write_bytes_unchecked(w, data_chunk)

        bytes_left -= len(data_chunk)
        if bytes_left < 0:
            raise ValueError("Bad response. Buffer overflow.")

    await layout.confirm_action_unknown(action.common, checksum.get_digest())


def _check_action(action: EosTxActionAck, name: str, account: str) -> bool:
    if account == "eosio":
        return (
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
        )

    elif name == "transfer":
        return action.transfer is not None

    elif action.unknown is not None:
        return True

    return False
