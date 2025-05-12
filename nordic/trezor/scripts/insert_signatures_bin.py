#!/usr/bin/env python3
"""
insert_signature.py

A script to append two TLV entries (signatures) into the unprotected TLV area
of a Zephyr image in raw binary format, updating the existing TLV-info header length.

Usage:
  python insert_signature.py input.bin <signature0> <signature1> [-o output.bin]

- `signature0` `signature1` and must be 64-byte values (128 hex digits).
"""
import argparse
import struct
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append signature TLVs to an existing unprotected TLV area in a Zephyr binary image.")
    # Input binary file to modify
    parser.add_argument('bin_file', help='Input raw binary file (.bin)')

    # Signature value (hex string) must represent exactly 64 bytes
    parser.add_argument(
        'signature0',
        help='Signature 0 as hex string (exactly 128 hex digits, e.g. 0xAA...AA or AA...AA)')

    # Signature value (hex string) must represent exactly 64 bytes
    parser.add_argument(
        'signature1',
        help='Signature 1 as hex string (exactly 128 hex digits, e.g. 0xAA...AA or AA...AA)')

    # Optional output file path
    parser.add_argument(
        '-o', '--output',
        help='Output binary file (defaults to input_inserted.bin)')

    return parser.parse_args()


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
    # Ensure hex string has even length
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


def main():
    args = parse_args()

    # Read entire binary into memory
    try:
        with open(args.bin_file, 'rb') as f:
            data = bytearray(f.read())  # use mutable bytearray for in-place update
    except FileNotFoundError:
        sys.exit(f"Error: File {args.bin_file} not found.")

    # Custom TLV tags
    TAG_SIGNATURE_0 = 0x00A0  # signature TLV tag
    TAG_SIGNATURE_1 = 0x00A1  # signature TLV tag

    # Build new TLV entries
    tlv_sig0  = make_tlv_entry(TAG_SIGNATURE_0, args.signature0, enforce_len=64)
    tlv_sig1  = make_tlv_entry(TAG_SIGNATURE_1, args.signature1, enforce_len=64)
    new_entries = tlv_sig0 + tlv_sig1

    # Magic marking start of unprotected TLV-info header
    IMAGE_TLV_INFO_MAGIC = 0x6907
    magic_bytes = struct.pack('<H', IMAGE_TLV_INFO_MAGIC)

    # Find the last occurrence of the magic in the file
    idx = data.rfind(magic_bytes)
    if idx == -1:
        sys.exit("Error: No unprotected TLV-info header magic found in file.")

    # Read the existing length (2 bytes following magic)
    old_len = struct.unpack_from('<H', data, idx + 2)[0]

    # Compute and write new length into header
    new_len = old_len + len(new_entries)
    struct.pack_into('<H', data, idx + 2, new_len)
    # Note: we do not modify magic or existing TLVs

    # Append only the new entries after the existing data
    data.extend(new_entries)

    # Determine output path
    out_file = args.output or args.bin_file.replace('.bin', '_inserted.bin')
    # Write updated binary
    with open(out_file, 'wb') as f:
        f.write(data)

    print(f"Updated TLV-info length from {old_len} to {new_len} and appended new entries. Output: {out_file}")


if __name__ == '__main__':
    main()
