    .syntax unified

#include "version.h"

    .section .header, "a"

    .type g_header, %object
    .size g_header, .-g_header

g_header:
    .byte 'T','R','Z','F'            // magic
    .word g_header_end - g_header    // hdrlen
#ifdef TREZOR_MODEL_T2T1
    .word 0                          // expiry
#else
    .word 1                          // expiry
#endif
    .word _codelen                   // codelen
    .byte VERSION_MAJOR              // vmajor
    .byte VERSION_MINOR              // vminor
    .byte VERSION_PATCH              // vpatch
    .byte VERSION_BUILD              // vbuild
    .byte FIX_VERSION_MAJOR          // fix_vmajor
    .byte FIX_VERSION_MINOR          // fix_vminor
    .byte FIX_VERSION_PATCH          // fix_vpatch
    .byte FIX_VERSION_BUILD          // fix_vbuild
    .word HW_MODEL                   // type of the designated hardware
    .byte HW_REVISION                // revision of the designated hardware
    .byte FIRMWARE_MONOTONIC_VERSION // monotonic version of the binary
    . = . + 2                        // reserved
    . = . + 512                      // hash1 ... hash16
    . = . + 415                      // reserved
    .byte 0                          // sigmask
    . = . + 64                       // sig
g_header_end:
