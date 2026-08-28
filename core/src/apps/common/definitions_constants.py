# generated from definitions_constants.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

MIN_DATA_VERSION = 1783520408
MAGIC = b"trzd"

# Supported format versions of the definitions, encoded on the wire as
# ASCII digit bytes ('1' = 0x31, '2' = 0x32, etc.).
SUPPORTED_FORMAT_VERSIONS = (b"1", b"2")

# The public keys and signature thresholds for definitions verification
# live in Rust (core/embed/rust/src/definitions/constants.rs).
