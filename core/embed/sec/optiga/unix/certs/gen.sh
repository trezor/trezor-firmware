#!/bin/sh

cd "$(dirname "$0")"
for file in *.der
do
    header_file="${file%.der}.h"
    echo "// This file was generated via ./gen.sh" > "$header_file"
    echo >> "$header_file"
    xxd -i "$file" | sed 's/unsigned/static const unsigned/' >> "$header_file"
    clang-format -i "$header_file"
done
