    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Firmware manifest ("firmware directory") for the Merkle-tree signing scheme,
// emitted at the very start of the firmware image (see firmware_pq.ld). It is
// the variant leaf of the firmware tree: variant_leaf = H(0x00 || manifest).
//
// Static fields are set here at build time: the magic, the firmware variant, and
// the module directory's shape (module_count + each entry's role/flags). The
// per-entry addr/size/header_hash are filled post-build (headertool_pq), since
// they depend on the linked layout and the (post-build) chunk hashes; app_root
// and translations_root are reserved (zero) until those subtrees exist.
//
// Layout matches firmware_manifest_t (sec/boot_header.h) and the signer/tool
// (tools/trezor_core_tools/firmware_module.py) byte-for-byte. The region is
// reserved to FW_MANIFEST_REGION (1K).

    .section .manifest, "a"

    .type g_firmware_manifest, %object
g_firmware_manifest:
    .byte 'T','R','Z','D'            // magic (FW_MANIFEST_MAGIC)
    .word FW_VARIANT                 // firmware_variant (fw_variant_t; from build.rs)
    .byte VERSION_MAJOR              // firmware_version.major  (same source as the
    .byte VERSION_MINOR              //   kernel+coreapp module header, version.h)
    .byte VERSION_PATCH              // firmware_version.patch
    .byte VERSION_BUILD              // firmware_version.build
    .space 32                        // app_root         (reserved; 0)
    .space 32                        // translations_root(reserved; 0)
    .word 2                          // module_count (secmon + kernel+coreapp)

    // entry[0]: secmon (the secure boot/entry module)
    .word 1                          // module_type = FW_MODULE_SECMON
    .word 1                          // flags = FW_MANIFEST_ENTRY_FLAG_BOOT
    .word 0                          // addr        (filled post-build)
    .word 0                          // size        (filled post-build)
    .space 32                        // header_hash  (filled post-build)

    // entry[1]: kernel+coreapp
    .word 2                          // module_type = FW_MODULE_APP (kernel+coreapp)
    .word 0                          // flags
    .word 0                          // addr        (filled post-build)
    .word 0                          // size        (filled post-build)
    .space 32                        // header_hash  (filled post-build)

    . = g_firmware_manifest + 0x400  // reserve FW_MANIFEST_REGION
    .size g_firmware_manifest, .-g_firmware_manifest
g_firmware_manifest_end:
