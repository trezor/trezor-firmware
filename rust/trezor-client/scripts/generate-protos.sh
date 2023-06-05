#!/bin/sh

# Generates src/protos/
# Requires the `protoc-gen-rust` binary (`cargo install protoc-gen-rust`).
# Overwrites src/protos/mod.rs, but the change should not be committed, and
# instead should be handled manually.

crate_root="$(dirname "$(dirname "$(realpath "$0")")")"
main_root="$(dirname $(dirname "$crate_root"))"
out_dir="$crate_root/src/protos"
proto_dir="$main_root/common/protob"

protoc \
    --proto_path "$proto_dir" \
    --rust_out "$out_dir" \
    "$proto_dir"/*.proto
