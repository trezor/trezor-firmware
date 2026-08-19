# generated from definitions_constants.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

MIN_DATA_VERSION = ${defs_timestamp}
MAGIC = b"trzd"

# Supported format versions of the definitions, encoded on the wire as
# ASCII digit bytes ('1' = 0x31, '2' = 0x32, etc.).
SUPPORTED_FORMAT_VERSIONS = (b"1",)

# The public keys and signature thresholds for definitions verification
# live in Rust (core/embed/rust/src/definitions/constants.rs).
