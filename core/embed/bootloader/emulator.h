#ifndef __EMULATOR_H__
#define __EMULATOR_H__

#define CLOCK_180_MHZ 0
#define mini_snprintf snprintf

#undef FIRMWARE_START

#include <stdint.h>
#include <stdio.h>

extern uint8_t *FIRMWARE_START;

void emulator_poll_events(void);
void set_core_clock(int);
__attribute__((noreturn)) void jump_to(uint32_t address);

#endif
