    .syntax unified

#include "version.h"

    .section .header, "a"

    .type g_header, %object
    .size g_header, .-g_header

g_header:
    .byte 'T','R','Z','B'            // magic
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
    . = . + 415                      // reserved
    .byte 0                          // sigmask
    . = . + 64                       // sig
g_header_end:
