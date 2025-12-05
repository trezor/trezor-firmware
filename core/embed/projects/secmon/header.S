    .syntax unified

#include "version.h"

    .section .secmon_header, "a"

    .type g_header, %object
    .size g_header, .-g_header

// Secure monitor header

g_header:
    .byte 'T','S','E','C'            // magic
    .word g_header_end - g_header    // hdrlen
    .word _codelen                   // codelen
    .byte VERSION_MAJOR              // vmajor
    .byte VERSION_MINOR              // vminor
    .byte VERSION_PATCH              // vpatch
    .byte VERSION_BUILD              // vbuild
    .word HW_MODEL                   // type of the designated hardware
    .byte HW_REVISION                // revision of the designated hardware
    .byte SECMON_MONOTONIC_VERSION   // monotonic version of the binary
    . = . + 2                        // reserved
    . = . + 32                       // hash of entire secmon
    . = . + 391                      // reserved
    .byte 0                          // sigmask
    . = . + 64                       // sig
g_header_end:

