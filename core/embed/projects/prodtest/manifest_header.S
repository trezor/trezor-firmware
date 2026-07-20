    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Firmware manifest ("firmware directory") for prodtest's Merkle-tree variant,
// emitted at the very start of the image (see prodtest_pq.ld). It is the
// variant leaf: variant_leaf = H(0x00 || manifest), which the founder tree folds
// into firmware_root. Prodtest is a SINGLE secure module, so the directory has
// exactly ONE entry (the prodtest module), flagged as the secure boot/entry
// module (FW_MANIFEST_ENTRY_FLAG_BOOT).
//
// Static fields (incl. the entry's addr/size, from linker symbols) are set here
// at build time; only the entry's code_hash is filled post-build (headertool_pq).
// Layout matches firmware_manifest_t (sec/boot_header.h) and the signer/tool
// (firmware_module.py) byte-for-byte.

    .section .manifest, "a"

    .type g_firmware_manifest, %object
g_firmware_manifest:
    .byte 'T','R','Z','D'            // magic (FW_MANIFEST_MAGIC)
    .word FW_VARIANT                 // firmware_variant (FW_VARIANT_PRODTEST; from build.rs)
    .byte VERSION_MAJOR              // firmware_version.major
    .byte VERSION_MINOR              // firmware_version.minor
    .byte VERSION_PATCH              // firmware_version.patch
    .byte VERSION_BUILD              // firmware_version.build
    .space 32                        // app_root         (reserved; 0)
    .space 32                        // translations_root(reserved; 0)
    .word 1                          // module_count (prodtest only)

    // entry[0]: prodtest (the sole secure boot/entry module)
    .word 3                          // module_type = FW_MODULE_PRODTEST
    .word 1                          // flags = FW_MANIFEST_ENTRY_FLAG_BOOT
    .word _manifest_module_addr      // addr (prodtest code offset; linker)
    .word _manifest_module_size      // size (prodtest code size; linker)
    .space 32                        // code_hash   (filled post-build)

    . = g_firmware_manifest + 0x400  // reserve FW_MANIFEST_REGION
    .size g_firmware_manifest, .-g_firmware_manifest
g_firmware_manifest_end:
