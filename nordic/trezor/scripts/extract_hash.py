#!/usr/bin/env python3
import re
import sys

def extract_sha256_from_file(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    collecting = False
    sha_record = False
    bytes_list = []

    for line in lines:

        if not sha_record:
            if "type: SHA256" in line:
                sha_record = True
            continue

        if not collecting:
            # look for the line that starts the data block
            m = re.match(r'\s*data:\s*(.*)$', line)
            if m:
                collecting = True
                # grab any 0x?? tokens on this same line
                bytes_list += re.findall(r'0x([0-9A-Fa-f]{2})', m.group(1))
        else:
            # continuation lines: indented and starting with 0x
            if re.match(r'\s*0x[0-9A-Fa-f]', line):
                bytes_list += re.findall(r'0x([0-9A-Fa-f]{2})', line)
            else:
                break  # end of the data block

    if not bytes_list:
        sys.exit("Error: No SHA256 data bytes found in file.")

    # join and print the full hash
    print(''.join(bytes_list).lower())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <dump.txt>", file=sys.stderr)
        sys.exit(1)
    extract_sha256_from_file(sys.argv[1])
