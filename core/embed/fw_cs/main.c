/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include STM32_HAL_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <display.h>
#include <mpu.h>
#include <touch.h>

#include "svc_numbers.h"
#include <embed/fw_ss/secure_api.h>

void jump_to_user_app(void) {
  asm volatile( "svc %0" : : "i"(CORE_SVC_START_APP));
}

void enum_callback(void* context, int secret) {
  display_printf("secret = %d\n", secret);
}

void core_init() {
  HAL_Init();
  mpu_config_cs();
  touch_init();
  display_reinit();
}

int main(void) {  // CORE SERVICES

  // Initialize hardware drivers
  core_init();

  display_printf("Core Services are running...\n");

  // Call a function in the secure world
  secure_enumerate_secrets(enum_callback, NULL);

  {
    uint8_t in_buff[64];
    uint8_t out_buff[64];

    // Test cmse_check_address_range() function
    // OK
    display_printf("%d\n", secure_process_buff(in_buff, sizeof(in_buff), out_buff, sizeof(out_buff)));
    // in_buff in secure memory
    display_printf("%d\n", secure_process_buff((void *)0x30000000, sizeof(in_buff), out_buff, sizeof(out_buff)));
    // out buff in secure memory
    display_printf("%d\n", secure_process_buff(in_buff, sizeof(in_buff), (void *)0x30000000, sizeof(out_buff)));
    // out buff in read only memory
    display_printf("%d\n", secure_process_buff(in_buff, sizeof(in_buff), (void *)0x08090000, sizeof(out_buff)));
  }


  HAL_Delay(500);  // uses Non-Secure SysTick

  // Configure MPU for the unprivileged application
  // isolate_unprivileged_world();

  // Jump to unprivileged user application
  jump_to_user_app();

  return 0;
}
