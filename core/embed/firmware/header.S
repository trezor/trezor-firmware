    .syntax unified

#include "version.h"

    .section .header, "a"

    .type g_header, %object
    .size g_header, .-g_header

// Firmware header for both Trezor One and Trezor T.
// Trezor One must have bootloader version >= 1.8.0 (before that version the hdrlen used to be reset vector)

g_header:
    .byte 'T','R','Z','F'            // magic
    .word g_header_end - g_header    // hdrlen
    .word 0                          // expiry
    .word _codelen                   // codelen
    .byte VERSION_MAJOR              // vmajor
    .byte VERSION_MINOR              // vminor
    .byte VERSION_PATCH              // vpatch
    .byte VERSION_BUILD              // vbuild
    .byte FIX_VERSION_MAJOR          // fix_vmajor
    .byte FIX_VERSION_MINOR          // fix_vminor
    .byte FIX_VERSION_PATCH          // fix_vpatch
    .byte FIX_VERSION_BUILD          // fix_vbuild
    . = . + 8                        // reserved
    . = . + 512                      // hash1 ... hash16

#if TREZOR_MODEL == T
// model T header specifics
    . = . + 415                      // reserved
    .byte 0                          // sigmask
    . = . + 64                       // sig
#elif TREZOR_MODEL == 1
// model 1 header specifics
    . = . + 64                       // sig1
    . = . + 64                       // sig2
    . = . + 64                       // sig3
    .byte 0                          // sigindex1
    .byte 0                          // sigindex2
    .byte 0                          // sigindex3
    . = . + 220                      // reserved
    . = . + 65                       // reserved
#else
#error Unknown Trezor model
#endif

g_header_end:

