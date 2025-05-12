#!/usr/bin/env python3
"""
insert_signature.py

A script to append two TLV entries (signature and sigmask) into the unprotected TLV area
of a Zephyr image in Intel HEX format, updating the existing TLV-info header length.

Usage:
  python insert_signature.py input.hex <signature> <sigmask> [-o output.hex]

- `signature` must be a 64-byte value (128 hex digits).
- `sigmask` can be any length hex string.
"""
import argparse
import struct
import sys
from intelhex import IntelHex


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append signature and sigmask TLVs to an existing unprotected TLV area in a Zephyr Intel HEX image.")
    # Input Intel HEX file to modify
    parser.add_argument('hex_file', help='Input Intel HEX file (.hex)')

    # Signature value (hex string) must represent exactly 64 bytes
    parser.add_argument(
        'signature',
        help='Signature as hex string (exactly 128 hex digits, e.g. 0xAA...AA or AA...AA)')

    # Sigmask value (hex string) of arbitrary length
    parser.add_argument(
        'sigmask',
        help='Sigmask as hex string (e.g. 0xBB.. or BB..)')

    # Optional output file path
    parser.add_argument(
        '-o', '--output',
        help='Output HEX file (defaults to input_inserted.hex)')

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
    # Ensure even number of hex digits
    if len(h) % 2:
        h = '0' + h
    # Convert to raw bytes
    val_bytes = bytes.fromhex(h)
    # Validate fixed length if required
    if enforce_len is not None and len(val_bytes) != enforce_len:
        sys.exit(
            f"Error: TLV for tag 0x{tag:04X} must be exactly {enforce_len} bytes, "
            f"but got {len(val_bytes)} bytes.")
    # Pack type (u16), length (u16), then payload
    return struct.pack('<HH', tag, len(val_bytes)) + val_bytes


def main():
    args = parse_args()

    # Load the entire Intel HEX into a byte array for modification
    try:
        ih = IntelHex(args.hex_file)
    except FileNotFoundError:
        sys.exit(f"Error: File {args.hex_file} not found.")

    # Determine continuous address range
    start_addr, end_addr = ih.minaddr(), ih.maxaddr()
    size = end_addr - start_addr + 1
    # Extract raw bytearray (mutable) from start to end
    data = bytearray(ih.tobinarray(start=start_addr, size=size))

    # Custom TLV tags
    TAG_SIGNATURE = 0x00A0  # signature TLV tag
    TAG_SIGMASK   = 0x00A1  # sigmask TLV tag

    # Build new TLV entries; enforce 64-byte signature
    tlv_sig  = make_tlv_entry(TAG_SIGNATURE, args.signature, enforce_len=64)
    tlv_mask = make_tlv_entry(TAG_SIGMASK,   args.sigmask)
    new_entries = tlv_sig + tlv_mask

    # Magic marking start of unprotected TLV-info header (2 bytes little-endian)
    IMAGE_TLV_INFO_MAGIC = 0x6907
    magic_bytes = struct.pack('<H', IMAGE_TLV_INFO_MAGIC)

    # Find the last occurrence of the magic within the data array
    idx = data.rfind(magic_bytes)
    if idx == -1:
        sys.exit("Error: No unprotected TLV-info header magic found in file.")

    # Read the existing length (2 bytes immediately following magic)
    old_len = struct.unpack_from('<H', data, idx + 2)[0]

    # Compute the new total length including our new entries
    new_len = old_len + len(new_entries)
    # Write the new length back into the data buffer
    struct.pack_into('<H', data, idx + 2, new_len)

    # Append only the new TLV entries (no extra magic)
    data.extend(new_entries)

    # Prepare a new IntelHex and write modified bytes back at correct addresses
    new_ih = IntelHex()
    for offset, byte in enumerate(data, start_addr):
        new_ih[offset] = byte

    # Determine output file path
    out_file = args.output or args.hex_file.replace('.hex', '_inserted.hex')
    new_ih.write_hex_file(out_file)

    print(f"Updated TLV-info length from {old_len} to {new_len} and appended new entries. Output: {out_file}")


if __name__ == '__main__':
    main()
