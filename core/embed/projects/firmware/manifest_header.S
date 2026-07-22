    .syntax unified

#include "version.h"
#include <trezor_model.h>

// Firmware manifest ("firmware directory") for the Merkle-tree signing scheme,
// emitted at the very start of the firmware image (see firmware_pq.ld). It is
// the variant leaf of the firmware tree: variant_leaf = H(0x00 || manifest).
//
// Static fields are set here at build time: the magic, the firmware variant, the
// module directory's shape (module_count + each entry's role/flags) and each
// entry's addr/size (from linker symbols -- the modules are linked in this
// image, so their code offsets/sizes are known). Only each entry's code_hash is
// filled post-build (headertool_pq), over the placed module code;
// translations_root is reserved (zero) until that subtree exists. The firmware
// Merkle proof after the manifest is zeroed here (node_count=0) and filled by
// the signer (firmware_pq_sign) once the founder firmware_root is known.
//
// Layout matches firmware_manifest_t + firmware_manifest_proof_t
// (sec/boot_header.h) and the signer/tool
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
    .space 32                        // translations_root(reserved; 0)
    .word 2                          // module_count (secmon + kernel+coreapp)

    // entry[0]: secmon (the secure boot/entry module)
    .word 1                          // module_type = FW_MODULE_SECMON
    .word 1                          // flags = FW_MANIFEST_ENTRY_FLAG_BOOT
    .word _manifest_secmon_addr      // addr (secmon code offset; linker)
    .word _manifest_secmon_size      // size (secmon code size; linker)
    .space 32                        // code_hash   (filled post-build)

    // entry[1]: kernel+coreapp
    .word 2                          // module_type = FW_MODULE_APP (kernel+coreapp)
    .word 0                          // flags
    .word _manifest_kernel_addr      // addr (kernel+coreapp code offset; linker)
    .word _manifest_kernel_size      // size (kernel+coreapp code size; linker)
    .space 32                        // code_hash   (filled post-build)

    // firmware Merkle proof (firmware_manifest_proof_t): the co-path folding
    // this variant's leaf up to firmware_root, filled post-build by the signer
    // (firmware_pq_sign). It sits right after the manifest, OUTSIDE the variant
    // leaf (the leaf covers only up to here), so the image carries its own proof
    // -- none is stored in the boot header. node_count=0 by default (single
    // variant, no fold); the signer overwrites it for a multi-variant tree.
    .word 0                          // firmware_proof.node_count (filled post-build)
    .space 4*32                      // firmware_proof.nodes[FW_MANIFEST_PROOF_MAX_NODES]

    . = g_firmware_manifest + 0x400  // reserve FW_MANIFEST_REGION
    .size g_firmware_manifest, .-g_firmware_manifest
g_firmware_manifest_end:
