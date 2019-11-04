from trezor.messages.NEMTransactionCommon import NEMTransactionCommon

from apps.common.writers import write_bytes, write_uint32_le, write_uint64_le

# https://github.com/nemtech/nem2-sdk-typescript-javascript/blob/master/src/infrastructure/catbuffer/TransactionBuilder.ts#L167
def serialize_tx_common(
    common: NEMTransactionCommon,
    public_key: bytearray,
    transaction_type: int,
    version: int = None,
) -> bytearray:
    w = bytearray()

    write_uint32_le(w, transaction_type)
    if version is None:
        version = common.network << 24 | 1
    write_uint32_le(w, version)

    write_bytes_with_len(w, public_key)
    write_uint64_le(w, common.max_fee)
    write_uint64_le(w, common.deadline)

    return w


def write_bytes_with_len(w, buf: bytes):
    write_uint32_le(w, len(buf))
    write_bytes(w, buf)
