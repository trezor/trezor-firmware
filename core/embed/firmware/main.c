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

#include "py/builtin.h"
#include "py/compile.h"
#include "py/gc.h"
#include "py/mperrno.h"
#include "py/nlr.h"
#include "py/repl.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "shared/runtime/pyexec.h"

#include "ports/stm32/gccollect.h"
#include "ports/stm32/pendsv.h"

#include "bl_check.h"
#include "board_capabilities.h"
#include "common.h"
#include "compiler_traits.h"
#include "display.h"
#include "flash.h"
#include "image.h"
#include "memzero.h"
#include "model.h"
#include "mpu.h"
#include "random_delays.h"
#include "rust_ui.h"
#include "sdcard.h"
#include "prodtest_common.h"

#include TREZOR_BOARD

#ifdef USE_RGB_LED
#include "rgb_led.h"
#endif
#ifdef USE_CONSUMPTION_MASK
#include "consumption_mask.h"
#endif
#ifdef USE_DMA2D
#include "dma2d.h"
#endif
#ifdef USE_BUTTON
#include "button.h"
#endif
#ifdef USE_I2C
#include "i2c.h"
#endif
#ifdef USE_TOUCH
#include "touch.h"
#endif
#ifdef USE_SD_CARD
#include "sdcard.h"
#endif
#ifdef USE_OPTIGA
#include "optiga_commands.h"
#include "optiga_transport.h"
#include "secret.h"
#endif
#include "unit_variant.h"

#ifdef SYSTEM_VIEW
#include "systemview.h"
#endif
#include "platform.h"
#include "rng.h"
#include "supervise.h"
#ifdef USE_SECP256K1_ZKP
#include "zkp_context.h"
#endif


#include "usb.h"

secbool startswith(const char *s, const char *prefix) {
  return sectrue * (0 == strncmp(s, prefix, strlen(prefix)));
}

static void vcp_intr(void) {
  display_clear();
  ensure(secfalse, "vcp_intr");
}

void vcp_readline(char *buf, size_t len) {
  uint32_t ticks_start = hal_ticks_ms();
  int received = 0;
  for (;;) {
    char c;
    int r = usb_vcp_read(VCP_IFACE, (uint8_t*)&c, 1);

    if (r<= 0) {
      if (received == 0 && hal_ticks_ms() - ticks_start > 1) {
        break;
      }
      continue;
    }

    received++;

    if (c == '\r') {
      vcp_puts("\r\n", 2);
      break;
    }
    if (c < 32 || c > 126) {  // not printable
      continue;
    }
    if (len > 1) {  // leave space for \0
      *buf = c;
      buf++;
      len--;
      vcp_puts(&c, 1);
    }
  }
  if (len > 0) {
    *buf = '\0';
  }
}

static void usb_init_all(void) {
  enum {
      VCP_PACKET_LEN = 64,
      VCP_BUFFER_LEN = 1024,
  };

  static const usb_dev_info_t dev_info = {
          .device_class = 0xEF,     // Composite Device Class
          .device_subclass = 0x02,  // Common Class
          .device_protocol = 0x01,  // Interface Association Descriptor
          .vendor_id = 0x1209,
          .product_id = 0x53C1,
          .release_num = 0x0400,
          .manufacturer = "SatoshiLabs",
          .product = "TREZOR",
          .serial_number = "000000000000",
          .interface = "TREZOR Interface",
          .usb21_enabled = secfalse,
          .usb21_landing = secfalse,
  };

  static uint8_t tx_packet[VCP_PACKET_LEN];
  static uint8_t tx_buffer[VCP_BUFFER_LEN];
  static uint8_t rx_packet[VCP_PACKET_LEN];
  static uint8_t rx_buffer[VCP_BUFFER_LEN];

  static const usb_vcp_info_t vcp_info = {
          .tx_packet = tx_packet,
          .tx_buffer = tx_buffer,
          .rx_packet = rx_packet,
          .rx_buffer = rx_buffer,
          .tx_buffer_len = VCP_BUFFER_LEN,
          .rx_buffer_len = VCP_BUFFER_LEN,
          .rx_intr_fn = vcp_intr,
          .rx_intr_byte = 3,  // Ctrl-C
          .iface_num = VCP_IFACE,
          .data_iface_num = 0x01,
          .ep_cmd = 0x82,
          .ep_in = 0x81,
          .ep_out = 0x01,
          .polling_interval = 10,
          .max_packet_len = VCP_PACKET_LEN,
  };

  usb_init(&dev_info);
  ensure(usb_vcp_add(&vcp_info), "usb_vcp_add");
  usb_start();
}


bool check_cnt(const flash_area_t * area, int * cnt){
  // assuming one subarea

  int size = flash_area_get_size(area);
  const uint32_t * addr = flash_area_get_address(area, 0, 0);

  bool clean = true;

  int zero_cnt = 0;
  int clean_words = 0;

  for (int i = 0; i < size / sizeof(uint32_t); i++ ){
    if (clean && addr[i] == 0){
      clean_words += 1;
      continue;
    } else if (clean) {
      uint32_t val = addr[i];

      bool one = false;
      zero_cnt = 0;


      for (int j = 0; j < 32; j++){
        if (val & (1 << j)){
          one = true;
        } else {
          if (one){
            return false;
          }
          zero_cnt++;
        }
      }

      clean = false;
    } else if (addr[i] != 0xFFFFFFFF) {
      return false;
    }
  }

  *cnt = 32 * clean_words + zero_cnt;

  return true;
}

void cnt_inc(const flash_area_t * area, uint32_t new_val) {

  uint32_t offset = (new_val / 32) * 4;

  uint32_t w = 0;
  if (new_val % 32 == 0){
    offset -= 4;
    w = 0;
  }else {
    w = 0xFFFFFFFF << (new_val % 32);

  }
  (void)!flash_unlock_write();

  (void)!flash_area_write_word(area, offset, w);

  (void)!flash_lock_write();
}

void write_fail(const flash_area_t * area, int test_idx) {
  (void)!flash_unlock_write();

  uint32_t byte_num = test_idx / 8;
  uint32_t bit_num = test_idx % 8;

  const uint8_t  * addr = flash_area_get_address(area, byte_num, 1);

  uint8_t prev = *addr;

  uint8_t new_val = prev & ~(1 << bit_num);

  (void)!flash_area_write_byte(area, byte_num, new_val);

  (void)!flash_lock_write();

}


// from util.s
extern void shutdown_privileged(void);

int main(void) {
  random_delays_init();

#ifdef RDI
  rdi_start();
#endif

  // reinitialize HAL for Trezor One
#if defined TREZOR_MODEL_1
  HAL_Init();
#endif

  collect_hw_entropy();

#ifdef SYSTEM_VIEW
  enable_systemview();
#endif

#ifdef USE_DMA2D
  dma2d_init();
#endif

  display_reinit();

  screen_boot_full();

#if !defined TREZOR_MODEL_1
  parse_boardloader_capabilities();

  unit_variant_init();

#ifdef USE_OPTIGA
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  secbool secret_ok =
      secret_read(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
#endif

#if PRODUCTION || BOOTLOADER_QA
  check_and_replace_bootloader();
#endif
  // Enable MPU
  //mpu_config_firmware();
#endif

  // Init peripherals
  pendsv_init();

#if !PRODUCTION
  // enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
#endif

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

#ifdef USE_I2C
  i2c_init();
#endif


#ifdef USE_TOUCH
  bool touch_available = touch_init();
#endif

#ifdef USE_SD_CARD
  sdcard_init();
#endif

#ifdef USE_OPTIGA
  optiga_init();
  optiga_open_application();
  if (sectrue == secret_ok) {
    optiga_sec_chan_handshake(secret, sizeof(secret));
  }
  memzero(secret, sizeof(secret));
#endif

#if !defined TREZOR_MODEL_1
  //drop_privileges();
#endif

#ifdef USE_SECP256K1_ZKP
  ensure(sectrue * (zkp_context_init() == 0), NULL);
#endif

  usb_init_all();

  sdcard_init();


  int cnt_success;
  int cnt_fail;

  if (!check_cnt(&STORAGE_AREAS[0], &cnt_success)) {
    (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
    (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
    (void)!flash_area_erase(&SECRET_AREA, NULL);
  }

  if (!check_cnt(&STORAGE_AREAS[1], &cnt_fail)) {
    (void)!flash_area_erase(&STORAGE_AREAS[1], NULL);
    (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
    (void)!flash_area_erase(&SECRET_AREA, NULL);
  }


  if (touch_available) {
    uint32_t r = sdtest_init(cnt_success, cnt_fail);

    if (r == 2) {
      (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
      (void)!flash_area_erase(&STORAGE_AREAS[1], NULL);
      (void)!flash_area_erase(&SECRET_AREA, NULL);
      cnt_success = 0;
      cnt_fail = 0;
    }
  }


  display_bar(0, 0, 240, 240, 0xE061);

  uint32_t data_wr[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
  uint32_t data_rd[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

  for(;;){

    uint32_t ticks = hal_ticks_ms();
    bool success = true;
    if (sdcard_is_present()) {
      sdcard_power_off();
      if (sectrue == sdcard_power_on()) {

        uint64_t cap = sdcard_get_capacity_in_bytes();

        if (cap == 0) {
          success = false;
        }
        else {
          uint32_t BLOCK_END = cap / SDCARD_BLOCK_SIZE - 1;
          uint32_t SDBACKUP_BLOCK_START = 0;
          uint32_t SDBACKUP_N_WRITINGS = 100;

          for (int i = 0; i < SDCARD_BLOCK_SIZE / sizeof(uint32_t); i++) {
            data_wr[i] = rng_get();
          }

          for (int n = 0; n < SDBACKUP_N_WRITINGS; n++) {
            uint32_t block = SDBACKUP_BLOCK_START + n * (BLOCK_END - SDBACKUP_BLOCK_START) / (SDBACKUP_N_WRITINGS - 1);
            data_wr[0] = block;
            success &= sectrue == sdcard_write_blocks(data_wr, block, 1);
          }

          sdcard_power_off();
          success &= sectrue == sdcard_power_on();

          for (int n = 0; n < SDBACKUP_N_WRITINGS; n++) {
            uint32_t block = SDBACKUP_BLOCK_START + n * (BLOCK_END - SDBACKUP_BLOCK_START) / (SDBACKUP_N_WRITINGS - 1);
            success &= sectrue == sdcard_read_blocks(data_rd, block, 1);
            data_wr[0] = block;
            success &= memcmp(data_wr, data_rd, SDCARD_BLOCK_SIZE) == 0;
          }
        }
      } else {
        success = false;
      }
    } else {
      success = false;
    }

    if (success)
    {
      cnt_success++;
      cnt_inc(&STORAGE_AREAS[0], cnt_success);
    } else {

      write_fail(&SECRET_AREA, cnt_fail + cnt_success);
      cnt_fail++;
      cnt_inc(&STORAGE_AREAS[1], cnt_fail);
    }

    sdtest_update(cnt_success, cnt_fail);


    char line[2048];  // expecting hundreds of bytes represented as hexadecimal
    // characters

    for (;;) {

      vcp_readline(line, sizeof(line));

      if (startswith(line, "PING")) {
        vcp_println("SUCCESS: %d, FAIL: %d", cnt_success, cnt_fail);

      } else if (startswith(line, "RESET")) {
        (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
        (void)!flash_area_erase(&STORAGE_AREAS[1], NULL);
        (void)!flash_area_erase(&SECRET_AREA, NULL);
        cnt_success = 0;
        cnt_fail = 0;
        sdtest_update(cnt_success, cnt_fail);
        vcp_println("OK");
      }else if (startswith(line, "STOP")) {
        vcp_println("SUCCESS: %d, FAIL: %d", cnt_success, cnt_fail);
        (void)!flash_area_erase(&STORAGE_AREAS[0], NULL);
        (void)!flash_area_erase(&STORAGE_AREAS[1], NULL);
        (void)!flash_area_erase(&SECRET_AREA, NULL);
        vcp_println("ERASED");
        cnt_success = 0;
        cnt_fail = 0;
        sdtest_update(cnt_success, cnt_fail);
        vcp_println("SUCCESS: %d, FAIL: %d", cnt_success, cnt_fail);
        vcp_println("HALT");
        for(;;);
      }

      uint32_t ticks_diff = hal_ticks_ms() - ticks;

      int delay = 10000 - ticks_diff;

      if (delay > 0) {
        hal_delay(1);
      } else {
        break;
      }
    }
  }



  printf("CORE: Preparing stack\n");
  // Stack limit should be less than real stack size, so we have a chance
  // to recover from limit hit.
  mp_stack_set_top(&_estack);
  mp_stack_set_limit((char *)&_estack - (char *)&_sstack - 1024);

#if MICROPY_ENABLE_PYSTACK
  static mp_obj_t pystack[1024];
  mp_pystack_init(pystack, &pystack[MP_ARRAY_SIZE(pystack)]);
#endif

  // GC init
  printf("CORE: Starting GC\n");
  gc_init(&_heap_start, &_heap_end);

  // Interpreter init
  printf("CORE: Starting interpreter\n");
  mp_init();
  mp_obj_list_init(mp_sys_argv, 0);
  mp_obj_list_init(mp_sys_path, 0);
  mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR__dot_frozen));

  // Execute the main script
  printf("CORE: Executing main script\n");
  pyexec_frozen_module("main.py");

  // Clean up
  printf("CORE: Main script finished, cleaning up\n");
  mp_deinit();

  // Python code shouldn't ever exit, avoid black screen if it does
  error_shutdown("INTERNAL ERROR", "(PE)");

  return 0;
}

// MicroPython default exception handler

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
  error_shutdown("INTERNAL ERROR", "(UE)");
}

// interrupt handlers

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("INTERNAL ERROR", "(CS)");
  }
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }

void MemManage_Handler_MM(void) { error_shutdown("INTERNAL ERROR", "(MM)"); }

void MemManage_Handler_SO(void) { error_shutdown("INTERNAL ERROR", "(SO)"); }

void BusFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(BF)"); }

void UsageFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(UF)"); }

// MicroPython builtin stubs

mp_import_stat_t mp_import_stat(const char *path) {
  return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
  return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);
