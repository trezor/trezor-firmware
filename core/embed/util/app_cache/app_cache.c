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

#ifdef KERNEL_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/applet.h>

#include <util/app_cache.h>
#include <util/elf_loader.h>

typedef struct {
  // Indicates whether an applet is loaded
  bool applet_loaded;
  // Loaded applet, valid if `applet_loaded` is true
  applet_t applet;
} app_cache_t;

static app_cache_t g_app_cache;

#ifndef TREZOR_EMULATOR
extern uint32_t _kernel_flash_end;
#define COREAPP_START COREAPP_CODE_ALIGN((uint32_t) & _kernel_flash_end)
#define COREAPP_END (FIRMWARE_START + FIRMWARE_MAXSIZE)
#endif

bool app_cache_spawn(const char* app_id, size_t app_id_size,
                     systask_id_t* task_id) {
  app_cache_t* cache = &g_app_cache;

  if (cache->applet_loaded) {
    return false;
  }

#ifdef TREZOR_EMULATOR
  if (!elf_load(&cache->applet,
                "../../../../trezor-app-emu-rust/target/debug/"
                "libtest_app_rust.so")) {
    return false;
  }
#else
  applet_layout_t temp_layout = {
      .code1 = {.start = APPCODE_START, .size = APPCODE_MAXSIZE},
      .data1 = {.start = APPDATA_RAM_START, .size = APPDATA_RAM_SIZE},
  };

  mpu_set_active_applet(&temp_layout);

  if (!elf_load((const void*)APPCODE_START, APPCODE_MAXSIZE,
                (void*)APPDATA_RAM_START, APPDATA_RAM_SIZE, &cache->applet)) {
    return false;
  }
#endif

  cache->applet_loaded = true;

  applet_run(&cache->applet);

  *task_id = cache->applet.task.id;

  return true;
}

void app_cache_unload(systask_id_t task_id) {
  app_cache_t* cache = &g_app_cache;

  if (cache->applet_loaded && cache->applet.task.id == task_id) {
    applet_unload(&cache->applet);
    cache->applet_loaded = false;
  }
}

#endif  // KERNEL_MODE
