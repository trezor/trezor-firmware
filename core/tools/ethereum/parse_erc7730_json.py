# /// script
# dependencies = ["erc7730"]
# ///

import io
import struct
import sys
from pathlib import Path

import click
from erc7730.common.abi import get_functions
from erc7730.model.display import FieldFormat
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputNestedFields,
    InputReference,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "python" / "src"))

from trezorlib import protobuf
from trezorlib.messages import (
    EthereumABITupleInfo,
    EthereumABIType,
    EthereumABIValueInfo,
    EthereumDisplayFormatInfo,
    EthereumERC7730ContainerPath,
    EthereumERC7730FieldFormatterType as FT,
    EthereumERC7730FieldInfo,
    EthereumERC7730Path,
)


def normalize_address(a) -> bytes:
    a = a.lower().lstrip("0x")
    if len(a) % 2 == 1:
        a = a + "0"  # TODO: why does this happen??
    return bytes.fromhex(a)


def is_dynamic_type(t, components):
    if t in ("string", "bytes"):
        return True
    if t == "tuple":
        return any(
            is_dynamic_type(c.type, getattr(c, "components", None) or [])
            for c in components
        )
    if t.endswith("[]"):
        return True
    return False


_ABI_TYPE_MAP: dict[str, tuple[bool, int]] = {
    "address": (False, EthereumABIType.ABI_ADDRESS),
    "bool": (False, EthereumABIType.ABI_BOOL),
    "bytes": (True, EthereumABIType.ABI_BYTES),
    "bytes4": (False, EthereumABIType.ABI_BYTES),
    "bytes8": (False, EthereumABIType.ABI_BYTES),
    "bytes32": (False, EthereumABIType.ABI_BYTES),
    "string": (True, EthereumABIType.ABI_STRING),
    "uint8": (False, EthereumABIType.ABI_UINT8),
    "uint16": (False, EthereumABIType.ABI_UINT16),
    "uint24": (False, EthereumABIType.ABI_UINT24),
    "uint32": (False, EthereumABIType.ABI_UINT32),
    "uint40": (False, EthereumABIType.ABI_UINT40),
    "uint48": (False, EthereumABIType.ABI_UINT48),
    "uint64": (False, EthereumABIType.ABI_UINT64),
    "uint72": (False, EthereumABIType.ABI_UINT72),
    "uint96": (False, EthereumABIType.ABI_UINT96),
    "uint112": (False, EthereumABIType.ABI_UINT112),
    "uint120": (False, EthereumABIType.ABI_UINT120),
    "uint128": (False, EthereumABIType.ABI_UINT128),
    "uint160": (False, EthereumABIType.ABI_UINT160),
    "uint248": (False, EthereumABIType.ABI_UINT248),
    "uint256": (False, EthereumABIType.ABI_UINT256),
}


def build_abi_value_info(t, components, is_in_array=False) -> EthereumABIValueInfo:
    if t.endswith("[]"):
        elem = build_abi_value_info(t[:-2], components, is_in_array=True)
        return EthereumABIValueInfo(array=elem)
    if t == "tuple":
        if any(c.type == "tuple" for c in components):
            raise TypeError("nested tuples not supported")
        fields = [
            build_abi_value_info(c.type, getattr(c, "components", None) or [], False)
            for c in components
        ]
        dynamic = False if is_in_array else is_dynamic_type(t, components)
        return EthereumABIValueInfo(
            tuple=EthereumABITupleInfo(fields=fields, is_dynamic=dynamic)
        )
    if t not in _ABI_TYPE_MAP:
        raise ValueError("unknown type: %s" % t)
    is_dynamic, abi_type = _ABI_TYPE_MAP[t]
    if is_dynamic:
        return EthereumABIValueInfo(dynamic=abi_type)
    return EthereumABIValueInfo(atomic=abi_type)


def path_to_proto(path_str, inputs) -> EthereumERC7730Path:
    if path_str in ("@.value", "$.value"):
        return EthereumERC7730Path(container_path=EthereumERC7730ContainerPath.VALUE)
    if path_str in ("@.from", "$.from"):
        return EthereumERC7730Path(container_path=EthereumERC7730ContainerPath.FROM)
    if path_str in ("@.to", "$.to"):
        return EthereumERC7730Path(container_path=EthereumERC7730ContainerPath.TO)
    if path_str.startswith("@"):
        raise ValueError("unsupported container path: %s" % path_str)

    if path_str.startswith("$."):
        path_str = path_str[2:]

    indices = []
    current_inputs = inputs

    for part in path_str.split("."):
        if part.startswith("[") and part.endswith("]"):
            inner = part[1:-1]
            if ":" in inner:
                raise ValueError("slice paths not supported in proto format")
            if inner:
                idx = int(inner)
                if idx < 0:
                    raise ValueError("negative path indices not supported in proto format")
                indices.append(idx)
        else:
            name_map = {p.name: i for i, p in enumerate(current_inputs)}
            if part not in name_map:
                raise ValueError(
                    "unknown field %r (available: %s)" % (part, list(name_map))
                )
            i = name_map[part]
            indices.append(i)
            components = getattr(current_inputs[i], "components", None) or []
            if components:
                current_inputs = components

    return EthereumERC7730Path(path=indices)


def build_field_info(field, func_inputs) -> EthereumERC7730FieldInfo | None:
    if field.path is None:
        return None

    try:
        path = path_to_proto(str(field.path), func_inputs)
    except ValueError as e:
        print("WARNING: skipping field %r: %s" % (field.label, e), file=sys.stderr)
        return None

    fmt = field.format
    params = field.params

    if fmt == FieldFormat.ADDRESS_NAME:
        return EthereumERC7730FieldInfo(
            path=path,
            label=field.label,
            formatter=FT.FORMATTER_ADDRESS_NAME,
        )
    if fmt == FieldFormat.AMOUNT:
        return EthereumERC7730FieldInfo(
            path=path,
            label=field.label,
            formatter=FT.FORMATTER_AMOUNT,
        )
    if fmt == FieldFormat.TOKEN_AMOUNT:
        token_path = None
        if params and params.tokenPath:
            try:
                token_path = path_to_proto(str(params.tokenPath), func_inputs)
            except ValueError as e:
                print(
                    "WARNING: dropping token_path for field %r: %s" % (field.label, e),
                    file=sys.stderr,
                )
        return EthereumERC7730FieldInfo(
            path=path,
            label=field.label,
            formatter=FT.FORMATTER_TOKEN_AMOUNT,
            token_path=token_path,
        )
    if fmt == FieldFormat.UNIT:
        kwargs: dict = {}
        if params.decimals is not None:
            kwargs["decimals"] = params.decimals
        if params.base:
            kwargs["base"] = params.base
        if params.prefix is not None:
            kwargs["prefix"] = params.prefix
        return EthereumERC7730FieldInfo(
            path=path,
            label=field.label,
            formatter=FT.FORMATTER_UNIT,
            **kwargs,
        )
    print("WARNING: unsupported formatter %s for field %r" % (fmt, field.label), file=sys.stderr)
    return None


def build_field_infos(display_fmt, func_inputs) -> list[EthereumERC7730FieldInfo]:
    result = []
    for field in display_fmt.fields:
        if isinstance(field, InputReference):
            print("WARNING: $ref %s not expanded, skipping" % field.ref, file=sys.stderr)
            continue
        if isinstance(field, InputNestedFields):
            print("WARNING: nested fields not supported, skipping", file=sys.stderr)
            continue
        info = build_field_info(field, func_inputs)
        if info is not None:
            result.append(info)
    return result


def get_intent(display_format) -> str:
    intent = display_format.intent
    if isinstance(intent, dict):
        return intent.get("en") or next(iter(intent.values()), "")
    return intent or ""


def build_display_format_infos(
    descriptor,
) -> list[EthereumDisplayFormatInfo]:
    deployments = descriptor.context.contract.deployments or []
    functions = get_functions(descriptor.context.contract.abi).functions
    # build a name→(selector_hex, function) map for non-hex sig lookup
    functions_by_name = {v.name: (k, v) for k, v in functions.items()}
    results = []

    for sig, display_format in descriptor.display.formats.items():
        if sig.startswith("0x"):
            func_sig_bytes = bytes.fromhex(sig[2:])
            function = functions[sig]
        else:
            func_name = sig.split("(")[0]
            if func_name not in functions_by_name:
                print(
                    "WARNING: skipping %s: not found in ABI" % sig, file=sys.stderr
                )
                continue
            selector_hex, function = functions_by_name[func_name]
            func_sig_bytes = bytes.fromhex(selector_hex[2:])

        parameter_defs = []
        skip = False
        for p in function.inputs:
            try:
                parameter_defs.append(
                    build_abi_value_info(p.type, getattr(p, "components", None) or [])
                )
            except (TypeError, ValueError) as e:
                print(
                    "WARNING: skipping function %s: parameter %r: %s"
                    % (sig, p.name, e),
                    file=sys.stderr,
                )
                skip = True
                break
        if skip:
            continue

        field_defs = build_field_infos(display_format, function.inputs)
        intent = get_intent(display_format)

        for deployment in deployments:
            results.append(
                EthereumDisplayFormatInfo(
                    chain_id=deployment.chainId,
                    address=normalize_address(deployment.address),
                    func_sig=func_sig_bytes,
                    intent=intent,
                    parameter_definitions=parameter_defs,
                    field_definitions=field_defs,
                )
            )

    return results


def serialize_message(msg) -> bytes:
    buf = io.BytesIO()
    protobuf.dump_message(buf, msg)
    data = buf.getvalue()
    return struct.pack("<I", len(data)) + data


@click.command()
@click.argument("filename")
@click.argument("output")
def main(filename, output):
    descriptor = InputERC7730Descriptor.load(Path(filename))
    infos = build_display_format_infos(descriptor)

    with open(output, "wb") as f:
        for info in infos:
            f.write(serialize_message(info))

    print("wrote %d record(s) to %s" % (len(infos), output))


if __name__ == "__main__":
    main()
