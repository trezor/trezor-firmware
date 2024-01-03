from typing import TYPE_CHECKING

from trezor.crypto.hashlib import sha256
from trezor.enums import (
    StellarSCAddressType,
    StellarSCValType,
    StellarSorobanAuthorizedFunctionType,
)
from trezor.utils import ensure
from trezor.wire import DataError

import apps.common.writers as writers

# Reexporting to other modules
write_bytes_fixed = writers.write_bytes_fixed
write_uint32 = writers.write_uint32_be
write_uint64 = writers.write_uint64_be

if TYPE_CHECKING:
    from typing import AnyStr

    from trezor.messages import (
        StellarInvokeContractArgs,
        StellarSCAddress,
        StellarSCVal,
        StellarSorobanAuthorizedFunction,
        StellarSorobanAuthorizedInvocation,
        StellarTxExt,
    )
    from trezor.utils import Writer


def _write_int(w: Writer, n: int, bits: int, bigendian: bool) -> int:
    ensure(-(2 ** (bits - 1)) <= n <= 2 ** (bits - 1) - 1, "overflow")
    shifts = range(0, bits, 8)
    if bigendian:
        shifts = reversed(shifts)
    for num in shifts:
        w.append((n >> num) & 0xFF)
    return bits // 8


def write_int32(w: Writer, n: int) -> int:
    return _write_int(w, n, 32, True)


def write_int64(w: Writer, n: int) -> int:
    return _write_int(w, n, 64, True)


def write_string(w: Writer, s: AnyStr) -> None:
    """Write XDR string padded to a multiple of 4 bytes."""
    # NOTE: 2 bytes smaller than if-else
    buf = s.encode() if isinstance(s, str) else s
    write_uint32(w, len(buf))
    writers.write_bytes_unchecked(w, buf)
    # if len isn't a multiple of 4, add padding bytes
    remainder = len(buf) % 4
    if remainder:
        writers.write_bytes_unchecked(w, bytes([0] * (4 - remainder)))


def write_bool(w: Writer, val: bool) -> None:
    # NOTE: 10 bytes smaller than if-else
    write_uint32(w, 1 if val else 0)


def write_pubkey(w: Writer, address: str) -> None:
    from .helpers import public_key_from_address

    # first 4 bytes of an address are the type, there's only one type (0)
    write_uint32(w, 0)
    writers.write_bytes_fixed(w, public_key_from_address(address), 32)


def write_contract(w: Writer, contract: str) -> None:
    from .helpers import decode_contract

    writers.write_bytes_fixed(w, decode_contract(contract), 32)


def write_sc_address(w: Writer, sc_address: StellarSCAddress) -> None:
    write_uint32(w, sc_address.type)
    if sc_address.type == StellarSCAddressType.SC_ADDRESS_TYPE_ACCOUNT:
        write_pubkey(w, sc_address.address)
    elif sc_address.type == StellarSCAddressType.SC_ADDRESS_TYPE_CONTRACT:
        write_contract(w, sc_address.address)
    else:
        raise DataError(f"Stellar: Unsupported SC address type: {sc_address.type}")


def write_sc_val(w: Writer, val: StellarSCVal) -> None:
    write_uint32(w, val.type)
    if val.type == StellarSCValType.SCV_BOOL:
        assert val.b is not None
        write_bool(w, val.b)
    elif val.type == StellarSCValType.SCV_VOID:
        pass  # nothing to write
    # SCV_ERROR NOT SUPPORTED
    elif val.type == StellarSCValType.SCV_U32:
        assert val.u32 is not None
        write_uint32(w, val.u32)
    elif val.type == StellarSCValType.SCV_I32:
        assert val.i32 is not None
        write_int32(w, val.i32)
    elif val.type == StellarSCValType.SCV_U64:
        assert val.u64 is not None
        write_uint64(w, val.u64)
    elif val.type == StellarSCValType.SCV_I64:
        assert val.i64 is not None
        write_int64(w, val.i64)
    elif val.type == StellarSCValType.SCV_TIMEPOINT:
        assert val.timepoint is not None
        write_uint64(w, val.timepoint)
    elif val.type == StellarSCValType.SCV_DURATION:
        assert val.duration is not None
        write_uint64(w, val.duration)
    elif val.type == StellarSCValType.SCV_U128:
        assert val.u128
        write_uint64(w, val.u128.hi)
        write_uint64(w, val.u128.lo)
    elif val.type == StellarSCValType.SCV_I128:
        assert val.i128
        write_int64(w, val.i128.hi)
        write_uint64(w, val.i128.lo)
    elif val.type == StellarSCValType.SCV_U256:
        assert val.u256
        write_uint64(w, val.u256.hi_hi)
        write_uint64(w, val.u256.hi_lo)
        write_uint64(w, val.u256.lo_hi)
        write_uint64(w, val.u256.lo_lo)
    elif val.type == StellarSCValType.SCV_I256:
        assert val.i256
        write_int64(w, val.i256.hi_hi)
        write_uint64(w, val.i256.hi_lo)
        write_uint64(w, val.i256.lo_hi)
        write_uint64(w, val.i256.lo_lo)
    elif val.type == StellarSCValType.SCV_BYTES:
        assert val.bytes is not None
        # if data len isn't a multiple of 4, add padding bytes
        write_bytes_fixed(
            w,
            val.bytes + bytes([0] * (4 - len(val.bytes) % 4)),
            len(val.bytes) + (4 - len(val.bytes) % 4),
        )
    elif val.type == StellarSCValType.SCV_STRING:
        assert val.string is not None
        write_string(w, val.string)
    elif val.type == StellarSCValType.SCV_SYMBOL:
        assert val.symbol is not None
        write_string(w, val.symbol)
    elif val.type == StellarSCValType.SCV_VEC:
        write_bool(w, True)
        write_uint32(w, len(val.vec))
        for item in val.vec:
            write_sc_val(w, item)
    elif val.type == StellarSCValType.SCV_MAP:
        write_bool(w, True)
        write_uint32(w, len(val.map))
        for item in val.map:
            assert item.key
            assert item.value
            write_sc_val(w, item.key)
            write_sc_val(w, item.value)
    elif val.type == StellarSCValType.SCV_ADDRESS:
        assert val.address
        write_sc_address(w, val.address)
    # SCV_CONTRACT_INSTANCE NOT SUPPORTED
    # SCV_LEDGER_KEY_CONTRACT_INSTANCE NOT SUPPORTED
    # SCV_LEDGER_KEY_NONCE NOT SUPPORTED
    else:
        raise DataError(f"Stellar: Unsupported SCV type: {val.type}")


def write_invoke_contract_args(
    w: Writer, invoke_contract_args: StellarInvokeContractArgs
) -> None:
    write_sc_address(w, invoke_contract_args.contract_address)
    write_string(w, invoke_contract_args.function_name)
    write_uint32(w, len(invoke_contract_args.args))
    for arg in invoke_contract_args.args:
        write_sc_val(w, arg)


def write_soroban_authorized_function(
    w: Writer, func: StellarSorobanAuthorizedFunction
) -> None:
    if (
        func.type
        != StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        raise DataError(f"Stellar: unsupported function type: {func.type}")
    assert func.contract_fn
    write_uint32(w, func.type)
    write_invoke_contract_args(w, func.contract_fn)


def write_soroban_authorized_invocation(
    w: Writer,
    invocation: StellarSorobanAuthorizedInvocation,
) -> None:
    write_soroban_authorized_function(w, invocation.function)
    write_uint32(w, len(invocation.sub_invocations))
    for sub_invocation in invocation.sub_invocations:
        write_soroban_authorized_invocation(w, sub_invocation)


def write_soroban_auth_info(
    w: Writer,
    network_passphrase: str,
    nonce: int,
    signature_expiration_ledger: int,
    invocation: StellarSorobanAuthorizedInvocation,
) -> None:
    write_uint32(w, 9)  # ENVELOPE_TYPE_SOROBAN_AUTHORIZATION = 9
    network_passphrase_hash = sha256(network_passphrase.encode()).digest()
    write_bytes_fixed(w, network_passphrase_hash, 32)
    write_int64(w, nonce)
    write_uint32(w, signature_expiration_ledger)
    write_soroban_authorized_invocation(w, invocation)


def write_tx_ext(w: Writer, tx_ext: StellarTxExt) -> None:
    write_int32(w, tx_ext.v)
    if tx_ext.v == 0:
        pass  # nothing to write
    elif tx_ext.v == 1:
        assert tx_ext.soroban_data
        write_bytes_fixed(w, tx_ext.soroban_data, len(tx_ext.soroban_data))
    else:
        raise DataError(f"Stellar: unsupported tx ext: {tx_ext.v}")
