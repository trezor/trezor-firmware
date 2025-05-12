#!/usr/bin/env python3
"""
insert_signatures.py

A script to append two TLV entries (signatures) into the unprotected TLV area
of a Zephyr image in either raw binary or Intel HEX format, updating the existing
TLV-info header length.

Usage:
  python insert_signatures.py input.[bin|hex] <signature0> <signature1> [-o output.[bin|hex]]

- `signature0` and `signature1` must be 64-byte values (128 hex digits).
"""
import argparse
import struct
import sys
import os
from intelhex import IntelHex


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append signature TLVs to an existing unprotected TLV area in a Zephyr image.")
    # Input file to modify
    parser.add_argument('input_file',
        help='Input file (.bin for raw binary or .hex for Intel HEX format)')

    # Signature values (hex strings) must represent exactly 64 bytes each
    parser.add_argument(
        'signature0',
        help='Signature 0 as hex string (exactly 128 hex digits, e.g. 0xAA...AA or AA...AA)')
    parser.add_argument(
        'signature1',
        help='Signature 1 as hex string (exactly 128 hex digits, e.g. 0xAA...AA or AA...AA)')

    # Optional output file path
    parser.add_argument(
        '-o', '--output',
        help='Output file (defaults to input_inserted.[bin|hex])')

    args = parser.parse_args()

    # Validate input file extension
    ext = os.path.splitext(args.input_file)[1].lower()
    if ext not in ['.bin', '.hex']:
        sys.exit("Error: Input file must have .bin or .hex extension")

    return args


def make_tlv_entry(tag, hexstr, enforce_len=None):
    """
    Build a TLV entry with:
      - 2-byte little-endian type
      - 2-byte little-endian length
      - payload bytes

    If `enforce_len` is set, the payload length must match exactly.
    """
    # Strip optional 0x/0X prefix
    h = hexstr[2:] if hexstr.lower().startswith('0x') else hexstr
    # Ensure even number of hex digits
    if len(h) % 2:
        h = '0' + h
    # Convert to bytes
    val_bytes = bytes.fromhex(h)
    # Validate fixed length if required
    if enforce_len is not None and len(val_bytes) != enforce_len:
        sys.exit(
            f"Error: TLV for tag 0x{tag:04X} must be exactly {enforce_len} bytes, "
            f"but got {len(val_bytes)} bytes.")
    # Pack type and length, then payload
    return struct.pack('<HH', tag, len(val_bytes)) + val_bytes


def process_binary_file(input_file):
    """Process raw binary input file."""
    try:
        with open(input_file, 'rb') as f:
            data = bytearray(f.read())
    except FileNotFoundError:
        sys.exit(f"Error: File {input_file} not found.")
    return data


def process_hex_file(input_file):
    """Process Intel HEX input file."""
    try:
        ih = IntelHex(input_file)
    except FileNotFoundError:
        sys.exit(f"Error: File {input_file} not found.")

    # Extract continuous range to bytearray
    start_addr = ih.minaddr()
    end_addr = ih.maxaddr()
    size = end_addr - start_addr + 1
    data = bytearray(ih.tobinarray(start=start_addr, size=size))

    return data, start_addr


def save_binary_file(data, output_file):
    """Save data as raw binary."""
    with open(output_file, 'wb') as f:
        f.write(data)


def save_hex_file(data, start_addr, output_file):
    """Save data as Intel HEX."""
    new_ih = IntelHex()
    for offset, byte in enumerate(data, start_addr):
        new_ih[offset] = byte
    new_ih.write_hex_file(output_file)


def main():
    args = parse_args()

    # Custom TLV tags
    TAG_SIGNATURE_0 = 0x00A0  # signature TLV tag
    TAG_SIGNATURE_1 = 0x00A1  # signature TLV tag

    # Build new TLV entries
    tlv_sig0 = make_tlv_entry(TAG_SIGNATURE_0, args.signature0, enforce_len=64)
    tlv_sig1 = make_tlv_entry(TAG_SIGNATURE_1, args.signature1, enforce_len=64)
    new_entries = tlv_sig0 + tlv_sig1

    # Process input based on file type
    is_hex = args.input_file.lower().endswith('.hex')
    if is_hex:
        data, start_addr = process_hex_file(args.input_file)
    else:
        data = process_binary_file(args.input_file)

    # Magic marking start of unprotected TLV-info header
    IMAGE_TLV_INFO_MAGIC = 0x6907
    magic_bytes = struct.pack('<H', IMAGE_TLV_INFO_MAGIC)

    # Find the last occurrence of the magic
    idx = data.rfind(magic_bytes)
    if idx == -1:
        sys.exit("Error: No unprotected TLV-info header magic found in file.")

    # Read and update the length
    old_len = struct.unpack_from('<H', data, idx + 2)[0]
    new_len = old_len + len(new_entries)
    struct.pack_into('<H', data, idx + 2, new_len)

    # Append the new entries
    data.extend(new_entries)

    # Determine output path and save
    if not args.output:
        base, ext = os.path.splitext(args.input_file)
        out_file = f"{base}_inserted{ext}"
    else:
        out_file = args.output

    if is_hex:
        save_hex_file(data, start_addr, out_file)
    else:
        save_binary_file(data, out_file)

    print(f"Updated TLV-info length from {old_len} to {new_len} and appended new entries. Output: {out_file}")


if __name__ == '__main__':
    main()
