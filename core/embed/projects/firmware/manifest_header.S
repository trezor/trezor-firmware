    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Firmware manifest ("firmware directory") at the start of the image; the
// variant leaf of the firmware tree. Design:
// docs/core/embed-arch/firmware-merkle-tree.md.
// Layout must match firmware_manifest_t + firmware_manifest_proof_t
// (sec/boot_header.h) and tools/trezor_core_tools/firmware_module.py
// byte-for-byte. code_hash and the proof are filled post-build.

    .section .manifest, "a"

    .type g_firmware_manifest, %object
g_firmware_manifest:
    .byte 'T','R','Z','D'            // magic (FW_MANIFEST_MAGIC)
    .word FW_VARIANT                 // firmware_variant (hardened; build.rs)
    .byte VERSION_MAJOR              // firmware_version.major
    .byte VERSION_MINOR              // firmware_version.minor
    .byte VERSION_PATCH              // firmware_version.patch
    .byte VERSION_BUILD              // firmware_version.build
    .space 32                        // translations_root(reserved; 0)
    .word 2                          // module_count (secmon + kernel+coreapp)

    // entry[0]: secmon (the secure boot/entry module)
    .word 1                          // module_type = FW_MODULE_SECMON
    .word 1                          // flags = FW_MANIFEST_ENTRY_FLAG_BOOT
    .word _manifest_secmon_addr      // addr (secmon code offset; linker)
    .word FW_CHUNK_SIZE              // chunk_size (from firmware_pq.ld)
    .word _manifest_secmon_size      // size (secmon code size; linker)
    .space 32                        // code_hash   (filled post-build)

    // entry[1]: kernel+coreapp
    .word 2                          // module_type = FW_MODULE_APP
    .word 0                          // flags
    .word _manifest_kernel_addr      // addr (kernel+coreapp offset; linker)
    .word FW_CHUNK_SIZE              // chunk_size (from firmware_pq.ld)
    .word _manifest_kernel_size      // size (kernel+coreapp code size; linker)
    .space 32                        // code_hash   (filled post-build)

    // Merkle proof to firmware_root, outside the variant leaf; filled by the
    // signer (node_count=0 until then)
    .word 0                          // firmware_proof.node_count
    .space 4*32                      // firmware_proof.nodes[]

    . = g_firmware_manifest + 0x400  // reserve FW_MANIFEST_REGION
    .size g_firmware_manifest, .-g_firmware_manifest
g_firmware_manifest_end:
