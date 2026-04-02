# /// script
# dependencies = ["erc7730"]
# ///

from binascii import hexlify
from eth_hash.auto import keccak
import click
import hashlib
from pathlib import Path
import re

from erc7730.common.abi import get_functions
from erc7730.model.display import FieldFormat
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputFieldDescription,
    InputNestedFields,
    InputReference,
)


def get_binding_context(descriptor):
    deployments = descriptor.context.contract.deployments
    if not deployments:
        return None

    pairs = ", ".join(
        "(%d, unhexlify(%r))" % (d.chainId, d.address.lower().lstrip("0x"))
        for d in deployments
    )

    return "BindingContext([%s])" % pairs


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


def get_parser(t, components, include_wrapper=True, is_in_array=False):
    if t.endswith("[]"):
        elem_type = t[:-2]
        elem_parser = get_parser(elem_type, components, is_in_array=True)
        return "Array(%s)" % elem_parser
    elif t == "tuple":
        members = ",\n                ".join(
            get_parser(c.type, getattr(c, "components", None) or [], False)
            + ",  # %s" % c.name
            for c in components
        )
        dynamic = False if is_in_array else is_dynamic_type(t, components)
        return (
            "Struct(\n            (\n                %s\n            ),\n            is_dynamic=%s,\n        )"
            % (members, dynamic)
        )
    elif t == "address":
        wrapper, parser = "Atomic", "parse_address"
    elif t == "bytes32":
        wrapper, parser = "Atomic", "parse_bytes"
    elif t == "string":
        wrapper, parser = "Dynamic", "parse_string"
    elif t == "bytes":
        wrapper, parser = "Dynamic", "parse_bytes"
    elif t == "uint256":
        wrapper, parser = "Atomic", "parse_uint256"
    elif t == "uint16":
        wrapper, parser = "Atomic", "parse_uint16"
    elif t == "uint32":
        wrapper, parser = "Atomic", "parse_uint32"
    elif t == "uint64":
        wrapper, parser = "Atomic", "parse_uint64"
    elif t == "int64":
        wrapper, parser = "Atomic", "parse_int64"
    elif t == "uint8":
        wrapper, parser = "Atomic", "parse_uint8"
    elif t == "uint128":
        wrapper, parser = "Atomic", "parse_uint128"
    elif t == "bytes8":
        wrapper, parser = "Atomic", "parse_bytes8"
    elif t == "bytes4":
        wrapper, parser = "Atomic", "parse_bytes4"
    elif t == "bool":
        wrapper, parser = "Atomic", "parse_bool"
    else:
        raise ValueError("Unknown type: %s" % t)

    if include_wrapper:
        return "%s(%s)" % (wrapper, parser)
    else:
        return parser

def path_to_indices(path_str, inputs):
    """Convert ERC7730 dot-path to index tuple, using ABI inputs for name→index lookup."""
    if path_str in ("@.value", "$.value"):
        return "ContainerPath.Value"
    if path_str in ("@.from", "$.from"):
        return "ContainerPath.From"
    if path_str.startswith("@"):
        return "ContainerPath.TODO"

    # strip leading "$." if present
    if path_str.startswith("$."):
        path_str = path_str[2:]

    indices = []
    current_inputs = inputs

    for part in path_str.split("."):
        if part.startswith("[") and part.endswith("]"):
            inner = part[1:-1]
            if ":" in inner:
                a, b = inner.split(":")
                indices.append((int(a), int(b)) if b else (int(a),))
            else:
                if inner:
                    indices.append(int(inner))
            # stay in current struct components (we're now inside an array element)
        else:
            name_map = {p.name: i for i, p in enumerate(current_inputs)}
            if part not in name_map:
                raise ValueError(
                    "Unknown field %r (available: %s)" % (part, list(name_map))
                )
            i = name_map[part]
            indices.append(i)
            # drill into struct components for the next level
            components = getattr(current_inputs[i], "components", None) or []
            if components:
                current_inputs = components

    return tuple(indices)


def get_formatter(field, func_inputs):
    fmt = field.format
    params = field.params

    if fmt == FieldFormat.ADDRESS_NAME:
        return "AddressNameFormatter"
    elif fmt == FieldFormat.AMOUNT:
        return "AmountFormatter"
    elif fmt == FieldFormat.TOKEN_AMOUNT:
        if params and params.tokenPath:
            token_path = path_to_indices(str(params.tokenPath), func_inputs)
            return "TokenAmountFormatter(token_path=%r)" % (token_path,)
        else:
            return "TokenAmountFormatter()"
    elif fmt == FieldFormat.UNIT:
        args = []
        if params.decimals is not None:
            args.append("decimals=%d" % params.decimals)
        if params.base:
            args.append("base=%r" % params.base)
        if params.prefix is not None:
            args.append("prefix=%s" % params.prefix)
        return "UnitFormatter(%s)" % ", ".join(args)
    elif fmt == FieldFormat.ENUM:
        return "TODOFormatter()"
    elif fmt == FieldFormat.RAW:
        return "TODOFormatter()"
    elif fmt == FieldFormat.CALL_DATA:
        return "TODOFormatter()"
    else:
        raise ValueError("Unsupported format: %s" % fmt)


def get_field_definitions(fmt, func_inputs):
    lines = []
    for field in fmt.fields:
        if isinstance(field, InputReference):
            print("        # WARNING: $ref %s not expanded" % field.ref)
            continue
        if isinstance(field, InputNestedFields):
            print("        # WARNING: nested fields not supported")
            continue
        # InputFieldDescription
        if field.path is None:
            continue
        path = path_to_indices(str(field.path), func_inputs)
        formatter = get_formatter(field, func_inputs)
        path_repr = path if isinstance(path, str) else repr(path)
        lines.append(
            "        FieldDefinition(%s, %r, %s)," % (path_repr, field.label, formatter)
        )
    return lines


def normalize_sig(sig):
    sig = re.sub(r'([\w\[\]]+)\s+\w+', r'\1', sig)  # strip param names
    sig = re.sub(r',\s+', ',', sig)  # strip spaces after commas
    return sig


@click.command()
@click.argument("filename")
def main(filename):
    descriptor = InputERC7730Descriptor.load(Path(filename))
    binding_context = get_binding_context(descriptor)
    print("""from ubinascii import unhexlify

from trezor.crypto import base58

from apps.ethereum.clear_signing import (
    AddressNameFormatter,
    AmountFormatter,
    Array,
    Atomic,
    BindingContext,
    ContainerPath,
    DisplayFormat,
    Dynamic,
    FieldDefinition,
    Struct,
    TokenAmountFormatter,
    UnitFormatter,
    TODOFormatter,
    parse_address,
    parse_bool,
    parse_bytes,
    parse_string,
    parse_uint8,
    parse_uint16,
    parse_uint24,
    parse_uint160,
    parse_uint256)""")
    print()

    print("BINDING_CONTEXT = %s" % binding_context)
    print()
    functions = get_functions(descriptor.context.contract.abi).functions
    print("DISPLAY_FORMATS = [")
    for sig, display_format in descriptor.display.formats.items():
        if not sig.startswith("0x"):
            func_sig = sig
            sig = normalize_sig(sig)
            sig = "0x" + hexlify(keccak(sig.encode())[:4]).decode("ascii")
        else:
            func_sig = None
        function = functions[sig]
        sig = sig[2:]
        print("    DisplayFormat(")
        print("        binding_context=BINDING_CONTEXT,")
        print("        func_sig=unhexlify(\"%s\"),%s" % (sig, "  # %s" % func_sig if func_sig else ""))
        print("        intent=\"%s\"," % display_format.intent)
        print("        parameter_definitions=[")
        for p in function.inputs:
            print("            %s, # %s" % (get_parser(p.type, p.components), p.name))
        print("        ],")
        print("        field_definitions=[")
        for line in get_field_definitions(display_format, function.inputs):
            print(line)
        print("        ],")
        print("    ),")
    print("]")


if __name__ == "__main__":
    main()
