from apps.common.writers import (
    write_bytes_fixed,
    write_bytes_unchecked,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le,
    write_uvarint,
)

if False:
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
        EosActionUpdateAuth,
        EosActionVoteProducer,
        EosAsset,
        EosAuthorization,
        EosTxHeader,
    )
    from trezor.utils import Writer


def write_auth(w: Writer, auth: EosAuthorization) -> None:
    write_uint32_le(w, auth.threshold)
    write_uvarint(w, len(auth.keys))
    for key in auth.keys:
        write_uvarint(w, key.type)
        write_bytes_fixed(w, key.key, 33)
        write_uint16_le(w, key.weight)

    write_uvarint(w, len(auth.accounts))
    for account in auth.accounts:
        write_uint64_le(w, account.account.actor)
        write_uint64_le(w, account.account.permission)
        write_uint16_le(w, account.weight)

    write_uvarint(w, len(auth.waits))
    for wait in auth.waits:
        write_uint32_le(w, wait.wait_sec)
        write_uint16_le(w, wait.weight)


def write_header(hasher: Writer, header: EosTxHeader) -> None:
    write_uint32_le(hasher, header.expiration)
    write_uint16_le(hasher, header.ref_block_num)
    write_uint32_le(hasher, header.ref_block_prefix)
    write_uvarint(hasher, header.max_net_usage_words)
    write_uint8(hasher, header.max_cpu_usage_ms)
    write_uvarint(hasher, header.delay_sec)


def write_action_transfer(w: Writer, msg: EosActionTransfer) -> None:
    write_uint64_le(w, msg.sender)
    write_uint64_le(w, msg.receiver)
    write_asset(w, msg.quantity)
    write_bytes_prefixed(w, msg.memo)


def write_action_buyram(w: Writer, msg: EosActionBuyRam) -> None:
    write_uint64_le(w, msg.payer)
    write_uint64_le(w, msg.receiver)
    write_asset(w, msg.quantity)


def write_action_buyrambytes(w: Writer, msg: EosActionBuyRamBytes) -> None:
    write_uint64_le(w, msg.payer)
    write_uint64_le(w, msg.receiver)
    write_uint32_le(w, msg.bytes)


def write_action_sellram(w: Writer, msg: EosActionSellRam) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.bytes)


def write_action_delegate(w: Writer, msg: EosActionDelegate) -> None:
    write_uint64_le(w, msg.sender)
    write_uint64_le(w, msg.receiver)
    write_asset(w, msg.net_quantity)
    write_asset(w, msg.cpu_quantity)
    write_uint8(w, 1 if msg.transfer else 0)


def write_action_undelegate(w: Writer, msg: EosActionUndelegate) -> None:
    write_uint64_le(w, msg.sender)
    write_uint64_le(w, msg.receiver)
    write_asset(w, msg.net_quantity)
    write_asset(w, msg.cpu_quantity)


def write_action_refund(w: Writer, msg: EosActionRefund) -> None:
    write_uint64_le(w, msg.owner)


def write_action_voteproducer(w: Writer, msg: EosActionVoteProducer) -> None:
    write_uint64_le(w, msg.voter)
    write_uint64_le(w, msg.proxy)
    write_uvarint(w, len(msg.producers))
    for producer in msg.producers:
        write_uint64_le(w, producer)


def write_action_updateauth(w: Writer, msg: EosActionUpdateAuth) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.permission)
    write_uint64_le(w, msg.parent)
    write_auth(w, msg.auth)


def write_action_deleteauth(w: Writer, msg: EosActionDeleteAuth) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.permission)


def write_action_linkauth(w: Writer, msg: EosActionLinkAuth) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.code)
    write_uint64_le(w, msg.type)
    write_uint64_le(w, msg.requirement)


def write_action_unlinkauth(w: Writer, msg: EosActionLinkAuth) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.code)
    write_uint64_le(w, msg.type)


def write_action_newaccount(w: Writer, msg: EosActionNewAccount) -> None:
    write_uint64_le(w, msg.creator)
    write_uint64_le(w, msg.name)
    write_auth(w, msg.owner)
    write_auth(w, msg.active)


def write_action_common(w: Writer, msg: EosActionCommon) -> None:
    write_uint64_le(w, msg.account)
    write_uint64_le(w, msg.name)
    write_uvarint(w, len(msg.authorization))
    for authorization in msg.authorization:
        write_uint64_le(w, authorization.actor)
        write_uint64_le(w, authorization.permission)


def write_asset(w: Writer, asset: EosAsset) -> None:
    write_uint64_le(w, asset.amount)
    write_uint64_le(w, asset.symbol)


def write_bytes_prefixed(w: Writer, data: bytes) -> None:
    write_uvarint(w, len(data))
    write_bytes_unchecked(w, data)
