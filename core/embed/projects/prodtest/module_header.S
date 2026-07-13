    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Prodtest module header (TRZM) for the Merkle-tree signing scheme, selected by
// the `pq_secure_boot` feature (see build.rs). Prodtest is a single secure module
// (its own variant), so this is the only module its manifest lists. It replaces
// the legacy vendor + image + secmon (TSEC) headers. Layout matches
// firmware_module_header_t.
//
// Static fields are emitted at build time; code_hash (SHA-256 over the whole
// module code) is filled post-build by the tree signer. The region is reserved
// to 1K so the code offset is stable.

    .section .header, "a"

    .type g_module_header, %object
g_module_header:
    .byte 'T','R','Z','M'            // magic (FW_MODULE_MAGIC)
    .word HW_MODEL                   // hw_model
    .word 3                          // module_type = FW_MODULE_PRODTEST
    .byte VERSION_MAJOR              // version.major
    .byte VERSION_MINOR              // version.minor
    .byte VERSION_PATCH              // version.patch
    .byte VERSION_BUILD              // version.build
    .word _codelen                   // code_size
    .space 32                        // code_hash (filled by the signer)
    . = g_module_header + 0x400      // reserve 1K (stable code offset)
    .size g_module_header, .-g_module_header
g_module_header_end:
