#include "version.h"

	.section  .header,"a",%progbits

	.type g_header, %object
	.size g_header, .-g_header

g_header:
	.byte 'T','R','Z','L'
	.word g_header_end - g_header
	.word 0   /* valid until */
	.word _codelen
	.byte VERSION_MAJOR
	.byte VERSION_MINOR
	.byte VERSION_PATCH
	.byte VERSION_BUILD
	. = . + 427 /* reserved */
	.byte 0    /* sigindex */
	. = . + 64 /* signatures */
g_header_end:
