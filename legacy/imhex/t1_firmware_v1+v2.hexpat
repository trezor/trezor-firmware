#pragma base_address 0x800FF00

#include "t1_firmware.pat"

u32 V1_HEADER_BASE = base();
u32 V2_HEADER_BASE = base() + 0x100;
u32 VTOR           = V2_HEADER_BASE + 0x400;

#define FW_MAGIC_OLD "TRZR"
#define FW_MAGIC_NEW "TRZF"

ImageHeader_v1 header_v1 @ V1_HEADER_BASE;
ImageHeader_v2 header_v2 @ V2_HEADER_BASE;
VectorTable vector_table @ VTOR;

// this could be out of bounds, just warn if VTOR and old pre-1.8.0 bootloader
// reset handlers are not the same
u32 reset_start_v1 = (header_v2.hdrlen_or_reset_handler_thumb & 0xFFFFFFFE);
if (reset_start_v1 != (vector_table.exceptions.reset)) {
    std::print("v1 reset handler differs from VTOR");
};

// another possible declaration of exception handler with masking
// u8 reset_start_vtor[256] @ (vector_table.exceptions.reset & 0xFFFFFFFE);
// declaration via ptr, needs mask out Thumb bit
// u8 *reset_start_v1_ptr : u32 @ (V2_HEADER_BASE + 0x4);

std::assert(header_v1.magic_old == FW_MAGIC_OLD, "Wrong OLD magic");
std::assert(header_v2.magic_new == FW_MAGIC_NEW, "Wrong NEW magic");

