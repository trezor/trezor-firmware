    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Firmware manifest for prodtest's Merkle-tree variant: a single module,
// flagged as the boot module. Layout must match firmware_manifest_t +
// firmware_manifest_proof_t (sec/boot_header.h) and firmware_module.py
// byte-for-byte. See firmware/manifest_header.S.

    .section .manifest, "a"

    .type g_firmware_manifest, %object
g_firmware_manifest:
    .byte 'T','R','Z','D'            // magic (FW_MANIFEST_MAGIC)
    .word FW_VARIANT                 // firmware_variant (PRODTEST; build.rs)
    .byte VERSION_MAJOR              // firmware_version.major
    .byte VERSION_MINOR              // firmware_version.minor
    .byte VERSION_PATCH              // firmware_version.patch
    .byte VERSION_BUILD              // firmware_version.build
    .space 32                        // translations_root(reserved; 0)
    .word 1                          // module_count (prodtest only)

    // entry[0]: prodtest (the sole secure boot/entry module)
    .word 3                          // module_type = FW_MODULE_PRODTEST
    .word 1                          // flags = FW_MANIFEST_ENTRY_FLAG_BOOT
    .word _manifest_module_addr      // addr (prodtest code offset; linker)
    .word FW_CHUNK_SIZE              // chunk_size (from prodtest_pq.ld)
    .word _manifest_module_size      // size (prodtest code size; linker)
    .space 32                        // code_hash   (filled post-build)

    // Merkle proof, outside the variant leaf; filled by the signer
    .word 0                          // firmware_proof.node_count
    .space 4*32                      // firmware_proof.nodes[]

    . = g_firmware_manifest + 0x400  // reserve FW_MANIFEST_REGION
    .size g_firmware_manifest, .-g_firmware_manifest
g_firmware_manifest_end:
