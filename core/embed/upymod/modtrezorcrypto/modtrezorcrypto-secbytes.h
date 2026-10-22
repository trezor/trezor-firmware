/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Stage A: type declaration only. Values typed secbytes are still bytes at
 * runtime; the type checker rejects slicing, hex(), logging and passing them
 * where bytes are expected. The native object follows with the vault. */

/// package: trezorcrypto.__init__
/// class secbytes:
///     """Opaque immutable secret. No buffer or plaintext interface."""
