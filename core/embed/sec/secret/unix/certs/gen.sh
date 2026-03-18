#!/bin/sh

cd "$(dirname "$0")"
for file in *.der
do
    header_file="${file%.der}.h"
    echo "// This file was generated via ./gen.sh" > "$header_file"
    echo >> "$header_file"
    xxd -i "$file" | sed '
        s/unsigned.*_der\[\]/static uint8_t mcu_device_cert\[MCU_ATTESTATION_MAX_CERT_SIZE\]/;
	s/unsigned.*_len/static size_t mcu_device_cert_size/' >> "$header_file"
    clang-format -i "$header_file"
done
