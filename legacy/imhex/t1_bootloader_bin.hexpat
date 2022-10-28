#pragma base_address 0x8000000

#include "t1_firmware.pat"

u32 VTOR = base();

VectorTable vector_table @ VTOR;


