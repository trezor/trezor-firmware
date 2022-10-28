#pragma base_address 0x8010000

#include "t1_firmware.pat"

u32 V2_HEADER_BASE = base();
u32 VTOR           = V2_HEADER_BASE + 0x400;

#define FW_MAGIC_NEW "TRZF"

ImageHeader_v2 header_v2 @ V2_HEADER_BASE;
VectorTable vector_table @ VTOR;

std::assert(header_v2.magic_new == FW_MAGIC_NEW, "Wrong NEW magic, expected TRFZ at start");


