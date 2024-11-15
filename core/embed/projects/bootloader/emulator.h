#ifndef __EMULATOR_H__
#define __EMULATOR_H__

#include <trezor_types.h>

#undef FIRMWARE_START

extern uint8_t *FIRMWARE_START;

__attribute__((noreturn)) void jump_to(uint32_t address);

#endif
