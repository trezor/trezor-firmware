from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError, ProcessError

import apps.common.writers as writers

# Reexporting to other modules
write_bytes_fixed = writers.write_bytes_fixed
write_bytes_unchecked = writers.write_bytes_unchecked
write_uint32 = writers.write_uint32_be
write_uint64 = writers.write_uint64_be

if TYPE_CHECKING:
    from buffer_types import StrOrBytes
    from typing import Callable, TypeVar

    from trezor.messages import (
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeContractArgs,
        StellarSCVal,
        StellarSCValMapEntry,
        StellarSorobanAuthorizedFunction,
        StellarSorobanAuthorizedInvocation,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )
    from trezor.utils import Writer

    T = TypeVar("T")


def write_string(w: Writer, s: StrOrBytes) -> int:
    """Write XDR string padded to a multiple of 4 bytes.
    Returns the length of the string written to the buffer (without padding).
    """
    # NOTE: 2 bytes smaller than if-else
    buf = s.encode() if isinstance(s, str) else s
    write_uint32(w, len(buf))
    writers.write_bytes_unchecked(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    remainder = len(buf) % 4
    if remainder:
        writers.write_bytes_unchecked(w, bytes([0] * (4 - remainder)))
    return len(buf)


def write_bool(w: Writer, val: bool) -> None:
    # NOTE: 10 bytes smaller than if-else
    write_uint32(w, 1 if val else 0)


def write_pubkey(w: Writer, address: str) -> None:
    from .helpers import public_key_from_address

    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    writers.write_bytes_fixed(w, public_key_from_address(address), 32)


_INT32_MIN = const(-0x8000_0000)
_INT32_MAX = const(0x7FFF_FFFF)
_UINT32_MASK = const(0xFFFF_FFFF)

_INT64_MIN = const(-0x8000_0000_0000_0000)
_INT64_MAX = const(0x7FFF_FFFF_FFFF_FFFF)
_UINT64_MASK = const(0xFFFF_FFFF_FFFF_FFFF)


def write_int32(w: Writer, value: int) -> None:
    """Write signed 32-bit integer in big-endian."""
    if value < _INT32_MIN or value > _INT32_MAX:
        raise ValueError("int32 out of range")
    write_uint32(w, value & _UINT32_MASK)


def write_int64(w: Writer, value: int) -> None:
    """Write signed 64-bit integer in big-endian."""
    if value < _INT64_MIN or value > _INT64_MAX:
        raise ValueError("int64 out of range")
    write_uint64(w, value & _UINT64_MASK)


def write_vec(
    w: Writer, items: list[T], write_item: Callable[[Writer, T], None]
) -> None:
    write_uint32(w, len(items))
    for item in items:
        write_item(w, item)


def write_invoke_contract_args(w: Writer, msg: StellarInvokeContractArgs) -> None:
    write_sc_address(w, msg.contract_address)
    _write_sc_symbol(w, msg.function_name)
    write_vec(w, msg.args, write_sc_val)


def write_sc_address(w: Writer, addr: str) -> None:
    from . import helpers

    version, data = helpers.decode_strkey(addr)

    if version == helpers.STRKEY_ED25519_PUBLIC_KEY:
        # AccountID is a PublicKey: KEY_TYPE_ED25519 (0) + 32 bytes ed25519
        write_uint32(w, 0)  # SC_ADDRESS_TYPE_ACCOUNT
        write_uint32(w, 0)  # KEY_TYPE_ED25519
        write_bytes_fixed(w, data, 32)
    elif version == helpers.STRKEY_CONTRACT:
        # ContractID is a Hash (32 bytes)
        write_uint32(w, 1)  # SC_ADDRESS_TYPE_CONTRACT
        write_bytes_fixed(w, data, 32)
    elif version == helpers.STRKEY_MUXED_ACCOUNT:
        # MuxedEd25519Account: { id: uint64, ed25519: uint256 }
        # address format: 32 bytes ed25519 + 8 bytes id
        write_uint32(w, 2)  # SC_ADDRESS_TYPE_MUXED_ACCOUNT
        write_bytes_fixed(w, data[32:40], 8)  # id (uint64)
        write_bytes_fixed(w, data[0:32], 32)  # ed25519
    elif version == helpers.STRKEY_CLAIMABLE_BALANCE:
        # ClaimableBalanceID: { type: uint32, v0: Hash }
        # address format: 1 byte type + 32 bytes hash (from strkey decoding);
        # decode_strkey has already checked that the type byte is v0
        write_uint32(w, 3)  # SC_ADDRESS_TYPE_CLAIMABLE_BALANCE
        write_uint32(w, 0)  # CLAIMABLE_BALANCE_ID_TYPE_V0
        write_bytes_fixed(w, data[1:33], 32)  # v0 hash
    elif version == helpers.STRKEY_LIQUIDITY_POOL:
        # PoolID is a Hash (32 bytes)
        write_uint32(w, 4)  # SC_ADDRESS_TYPE_LIQUIDITY_POOL
        write_bytes_fixed(w, data, 32)
    else:
        raise ProcessError("Stellar: unsupported SC address type")


def _write_sc_symbol(w: Writer, symbol: str) -> None:
    from . import consts

    written = write_string(w, symbol)
    if written > consts.SCSYMBOL_MAX_SIZE:
        raise DataError("Stellar: symbol too long")


def write_sc_val(w: Writer, msg: StellarSCVal) -> None:
    from trezor.enums import StellarSCValType

    write_uint32(w, msg.type)

    if msg.type == StellarSCValType.SCV_BOOL:
        if msg.b is None:
            raise DataError("Stellar: missing bool value")
        write_bool(w, msg.b)
    elif msg.type == StellarSCValType.SCV_VOID:
        pass  # no data
    elif msg.type == StellarSCValType.SCV_U32:
        if msg.u32 is None:
            raise DataError("Stellar: missing u32 value")
        write_uint32(w, msg.u32)
    elif msg.type == StellarSCValType.SCV_I32:
        if msg.i32 is None:
            raise DataError("Stellar: missing i32 value")
        write_int32(w, msg.i32)
    elif msg.type == StellarSCValType.SCV_U64:
        if msg.u64 is None:
            raise DataError("Stellar: missing u64 value")
        write_uint64(w, msg.u64)
    elif msg.type == StellarSCValType.SCV_I64:
        if msg.i64 is None:
            raise DataError("Stellar: missing i64 value")
        write_int64(w, msg.i64)
    elif msg.type == StellarSCValType.SCV_TIMEPOINT:
        if msg.timepoint is None:
            raise DataError("Stellar: missing timepoint value")
        write_uint64(w, msg.timepoint)
    elif msg.type == StellarSCValType.SCV_DURATION:
        if msg.duration is None:
            raise DataError("Stellar: missing duration value")
        write_uint64(w, msg.duration)
    elif msg.type == StellarSCValType.SCV_U128:
        if msg.u128 is None:
            raise DataError("Stellar: missing u128 value")
        _write_uint128_parts(w, msg.u128)
    elif msg.type == StellarSCValType.SCV_I128:
        if msg.i128 is None:
            raise DataError("Stellar: missing i128 value")
        _write_int128_parts(w, msg.i128)
    elif msg.type == StellarSCValType.SCV_U256:
        if msg.u256 is None:
            raise DataError("Stellar: missing u256 value")
        _write_uint256_parts(w, msg.u256)
    elif msg.type == StellarSCValType.SCV_I256:
        if msg.i256 is None:
            raise DataError("Stellar: missing i256 value")
        _write_int256_parts(w, msg.i256)
    elif msg.type == StellarSCValType.SCV_BYTES:
        if msg.bytes is None:
            raise DataError("Stellar: missing bytes value")
        write_string(w, msg.bytes)
    elif msg.type == StellarSCValType.SCV_STRING:
        if msg.string is None:
            raise DataError("Stellar: missing string value")
        write_string(w, msg.string)
    elif msg.type == StellarSCValType.SCV_SYMBOL:
        if msg.symbol is None:
            raise DataError("Stellar: missing symbol value")
        _write_sc_symbol(w, msg.symbol)
    elif msg.type == StellarSCValType.SCV_VEC:
        # In XDR the vector is a pointer (SCVec*), i.e. nullable, but a null vector
        # is not a valid Soroban value (only Some([...]), possibly empty). Here it
        # is a `repeated` field that is always a list, never None, so encoding it
        # as present is correct.
        write_bool(w, True)  # present
        write_vec(w, msg.vec, write_sc_val)
    elif msg.type == StellarSCValType.SCV_MAP:
        # map is a pointer (SCMap*) in XDR; same reasoning as SCV_VEC above.
        write_bool(w, True)  # present
        write_vec(w, msg.map, _write_sc_map_entry)
    elif msg.type == StellarSCValType.SCV_ADDRESS:
        if msg.address is None:
            raise DataError("Stellar: missing address value")
        write_sc_address(w, msg.address)
    else:
        raise ProcessError("Stellar: unsupported SCVal type")


def _write_sc_map_entry(w: Writer, entry: StellarSCValMapEntry) -> None:
    write_sc_val(w, entry.key)
    write_sc_val(w, entry.value)


def _write_uint128_parts(w: Writer, msg: StellarUInt128Parts) -> None:
    write_uint64(w, msg.hi)
    write_uint64(w, msg.lo)


def _write_int128_parts(w: Writer, msg: StellarInt128Parts) -> None:
    write_int64(w, msg.hi)
    write_uint64(w, msg.lo)


def _write_uint256_parts(w: Writer, msg: StellarUInt256Parts) -> None:
    write_uint64(w, msg.hi_hi)
    write_uint64(w, msg.hi_lo)
    write_uint64(w, msg.lo_hi)
    write_uint64(w, msg.lo_lo)


def _write_int256_parts(w: Writer, msg: StellarInt256Parts) -> None:
    write_int64(w, msg.hi_hi)
    write_uint64(w, msg.hi_lo)
    write_uint64(w, msg.lo_hi)
    write_uint64(w, msg.lo_lo)


def write_soroban_authorized_invocation(
    w: Writer, msg: StellarSorobanAuthorizedInvocation
) -> None:
    _write_soroban_authorized_function(w, msg.function)
    write_vec(w, msg.sub_invocations, write_soroban_authorized_invocation)


def _write_soroban_authorized_function(
    w: Writer, msg: StellarSorobanAuthorizedFunction
) -> None:
    from trezor.enums import StellarSorobanAuthorizedFunctionType

    write_uint32(w, msg.type)
    if (
        msg.type
        == StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        if msg.contract_fn is None:
            raise DataError("Stellar: missing contract_fn")
        write_invoke_contract_args(w, msg.contract_fn)
    else:
        raise ProcessError("Stellar: unsupported authorized function type")
