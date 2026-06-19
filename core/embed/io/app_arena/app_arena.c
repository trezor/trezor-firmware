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

#include <io/app_arena.h>
#include <sys/applet.h>
#include <sys/sysevent_source.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#include <stdlib.h>

#include "xbin_loader.h"

// Maximum number of application images that can be loaded in the arena
// at the same time. If more images are needed, this can be increased
// but the implementation of area memory management needs to be revisited.
#define APP_ARENA_MAX_IMAGES 1

// TLS for event handling
typedef struct {
  bool event_pending;
} app_arena_tls_t;

// Information about a loaded application image in the arena
typedef struct {
  // Handle of the loaded image
  app_image_handle_t handle;
  // Set if image was verified successfully
  bool verified;
  // Set if image is currently running
  bool running;

  // Reserved memory for the application
  void* mem_ptr;
  // Reserved memory size
  size_t mem_size;
  // Number of bytes of the image loaded into the reserved memory
  // (the rest of the reserved memory is used for rwdata)
  size_t image_size;

  // Applet associated with the application
  applet_t applet;

} app_arena_entry_t;

typedef struct {
  // Indicates whether the arena is initialized
  bool initialized;

  // Base pointer to the arena memory
  uint8_t* mem_ptr;
  // Total size of the arena memory
  size_t mem_size;
  // Amount of arena memory currently used by loaded images
  size_t mem_used;

  // TLS for for event handling
  app_arena_tls_t tls[SYSTASK_MAX_TASKS];
  // Set if a systask associated with any loaded image has been killed
  bool task_killed;

  // Next handle value to assign for a new image.
  // Handles are never reused, so this is just incremented for each new image.
  app_image_handle_t next_handle;

  // Slots for loaded images
  app_arena_entry_t images[APP_ARENA_MAX_IMAGES];

} app_arena_t;

static app_arena_t g_app_arena = {
    .initialized = false,
};

static const syshandle_vmt_t g_app_arena_handle_vmt;

ts_t app_arena_init(void) {
  app_arena_t* arena = &g_app_arena;

  if (arena->initialized) {
    return TS_OK;
  }

  TSH_DECLARE;

  memset(arena, 0, sizeof(app_arena_t));

  arena->next_handle = APP_IMAGE_HANDLE_INVALID + 1;

#ifdef TREZOR_EMULATOR
  arena->mem_size = 64 * 1024 * 1024;
  arena->mem_ptr = malloc(arena->mem_size);
  TSH_CHECK(arena->mem_ptr != NULL, TS_ENOMEM);
#else
  arena->mem_size = APPDATA_RAM_SIZE;
  arena->mem_ptr = (uint8_t*)APPDATA_RAM_START;
  TSH_CHECK(arena->mem_ptr != NULL, TS_ENOMEM);

#ifdef USE_TRUSTZONE
  // Allow unprivileged access to app arena memory
  tz_set_sram_unpriv(APPDATA_RAM_START, APPDATA_RAM_SIZE, true);
  // Allow unprivileged access to app code area
  tz_set_flash_unpriv(APPCODE_START, APPCODE_MAXSIZE, true);
#endif

#endif

  bool ok =
      syshandle_register(SYSHANDLE_APP_ARENA, &g_app_arena_handle_vmt, arena);
  TSH_CHECK(ok, TS_EINVAL);

  arena->initialized = true;

cleanup:
  TSH_RETURN;
}

ts_t app_arena_get_info(app_arena_info_t* info) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(info != NULL, TS_EINVAL);

  memset(info, 0, sizeof(*info));

  size_t image_count = 0;
  for (size_t i = 0; i < ARRAY_LENGTH(arena->images); i++) {
    if (arena->images[i].handle != APP_IMAGE_HANDLE_INVALID) {
      image_count++;
    }
  }

  info->total_size = arena->mem_size;
  info->free_size = arena->mem_size - arena->mem_used;
  info->image_count = image_count;

cleanup:
  TSH_RETURN;
}

ts_t app_arena_get_image_by_index(size_t idx, app_image_handle_t* handle) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(handle != NULL, TS_EINVAL);
  TSH_CHECK(idx < APP_ARENA_MAX_IMAGES, TS_EINVAL);

  *handle = APP_IMAGE_HANDLE_INVALID;

  // Iterate through the images and find the idx-th valid image
  for (size_t i = 0; i < ARRAY_LENGTH(arena->images); i++) {
    app_arena_entry_t* entry = &arena->images[i];
    if (entry->handle != APP_IMAGE_HANDLE_INVALID) {
      if (idx == 0) {
        *handle = entry->handle;
        break;
      }
      --idx;
    }
  }

cleanup:
  TSH_RETURN;
}

ts_t app_arena_create_image(app_image_handle_t* handle) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(handle != NULL, TS_EINVAL);

  *handle = APP_IMAGE_HANDLE_INVALID;

  TSH_CHECK(arena->mem_used < arena->mem_size, TS_ENOMEM);

  // Find an empty slot in the arena
  for (size_t i = 0; i < ARRAY_LENGTH(arena->images); i++) {
    app_arena_entry_t* entry = &arena->images[i];
    if (entry->handle == APP_IMAGE_HANDLE_INVALID) {
      memset(entry, 0, sizeof(*entry));
      // Allocate memory, for simplicity, we allow only using the whole arena.
      entry->mem_ptr = arena->mem_ptr + arena->mem_used;
      entry->mem_size = arena->mem_size - arena->mem_used;
      arena->mem_used += entry->mem_size;
      // Assign a new handle and mark the entry as loading
      entry->handle = arena->next_handle++;
      entry->verified = false;
      entry->running = false;

      *handle = entry->handle;
      break;
    }
  }

  TSH_CHECK(*handle != APP_IMAGE_HANDLE_INVALID, TS_ENOMEM);

cleanup:
  TSH_RETURN;
}

static void app_arena_configure_mpu(const app_arena_entry_t* entry) {
#ifndef TREZOR_EMULATOR
  applet_layout_t layout = {
      .data1 = {.start = (uintptr_t)entry->mem_ptr, .size = entry->mem_size},
  };
  mpu_set_active_applet(&layout);
#endif
}

static void app_arena_restore_mpu(void) {
#ifndef TREZOR_EMULATOR
  systask_set_mpu(systask_active());
#endif
}

static app_arena_entry_t* find_image_by_handle(app_image_handle_t handle) {
  app_arena_t* arena = &g_app_arena;

  if (!arena->initialized || handle == APP_IMAGE_HANDLE_INVALID) {
    return NULL;
  }

  for (size_t i = 0; i < ARRAY_LENGTH(arena->images); i++) {
    app_arena_entry_t* entry = &arena->images[i];
    if (entry->handle == handle) {
      return entry;
    }
  }

  return NULL;
}

ts_t app_image_get_info(app_image_handle_t handle, app_image_info_t* info) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(info != NULL, TS_EINVAL);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  app_image_info_t temp_info = {
      .verified = entry->verified,
      .running = entry->running,
      .image_size = entry->image_size,
  };

  if (entry->verified) {
    const xbin_header_t* header = (const xbin_header_t*)entry->mem_ptr;

    // We copy ID from one applet to another
    app_arena_configure_mpu(entry);
    temp_info.version = header->version;
    memcpy(temp_info.id, header->id, sizeof(temp_info.id));
    app_arena_restore_mpu();
  }

  if (entry->running) {
    temp_info.task_id = systask_id(&entry->applet.task);
  }

  *info = temp_info;

cleanup:
  TSH_RETURN;
}

ts_t app_image_delete(app_image_handle_t handle) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  if (entry->running) {
    app_image_stop(handle);
  }

  // Free the allocated memory
  arena->mem_used -= entry->mem_size;

  // Invalidate the entry
  memset(entry, 0, sizeof(*entry));

cleanup:
  TSH_RETURN;
}

ts_t app_image_write_chunk(app_image_handle_t handle, const void* data,
                           size_t size) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(data != NULL, TS_EINVAL);
  TSH_CHECK(size > 0, TS_EINVAL);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);
  TSH_CHECK(!entry->verified, TS_EINVAL);

  if (entry->image_size + size < entry->image_size ||
      entry->image_size + size > entry->mem_size) {
    // Not enough space in the arena for the new data
    TSH_CHECK_OK(TS_ENOMEM);
  }

  const uint8_t* src = data;
  const uint8_t* src_end = src + size;
  uint8_t* dst = (uint8_t*)entry->mem_ptr + entry->image_size;

  while (src < src_end) {
    uint8_t temp[256];

    size_t bytes_to_copy = MIN(src_end - src, sizeof(temp));

    // We are copying data between two memory areas that are not
    // accessible at the same time due to MPU restrictions.
    memcpy(temp, src, bytes_to_copy);
    app_arena_configure_mpu(entry);
    memcpy(dst, temp, bytes_to_copy);
    app_arena_restore_mpu();

    src += bytes_to_copy;
    dst += bytes_to_copy;
  }

  entry->image_size += size;

cleanup:
  TSH_RETURN;
}

ts_t app_image_verify(app_image_handle_t handle, const void* proof,
                      size_t proof_size) {
  TSH_DECLARE;
  ts_t status;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  TSH_CHECK(IS_ALIGNED(proof_size, 32), TS_EINVAL);
  TSH_CHECK(proof_size == 0 || proof != NULL, TS_EINVAL);

  TSH_CHECK(!entry->verified, TS_EINVAL);

  app_arena_configure_mpu(entry);

  const xbin_header_t* header =
      xbin_verify_image(entry->mem_ptr, entry->image_size);
  TSH_CHECK(header != NULL, TS_EINVAL);

  status = xbin_verify_signature(header, proof, proof_size);
  TSH_CHECK_OK(status);

  entry->verified = true;

cleanup:
  app_arena_restore_mpu();
  TSH_RETURN;
}

ts_t app_image_run(app_image_handle_t handle, systask_id_t* task_id) {
  TSH_DECLARE;
  ts_t status;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);

  TSH_CHECK(task_id != NULL, TS_EINVAL);
  *task_id = 0;

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  TSH_CHECK(entry->verified, TS_EINVAL);

  if (entry->running) {
    *task_id = entry->applet.task.id;
  } else {
    size_t rwmem_size = entry->mem_size - entry->image_size;
    void* rwmem = (uint8_t*)entry->mem_ptr + entry->image_size;

    app_arena_configure_mpu(entry);

    const xbin_header_t* header = (const xbin_header_t*)entry->mem_ptr;
    status = xbin_prepare_applet(header, rwmem, rwmem_size, &entry->applet);
    TSH_CHECK_OK(status);

    entry->running = true;
    applet_run(&entry->applet);

    *task_id = entry->applet.task.id;
  }

cleanup:
  app_arena_restore_mpu();
  TSH_RETURN;
}

ts_t app_image_stop(app_image_handle_t handle) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  if (entry->running) {
    applet_unload(&entry->applet);

    memset(&entry->applet, 0, sizeof(entry->applet));
    entry->running = false;
  }

cleanup:
  TSH_RETURN;
}

ts_t app_image_get_pminfo(app_image_handle_t handle,
                          systask_postmortem_t* pminfo) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);
  TSH_CHECK(pminfo != NULL, TS_EINVAL);

  app_arena_entry_t* entry = find_image_by_handle(handle);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  *pminfo = entry->applet.task.pminfo;

cleanup:
  TSH_RETURN;
}

ts_t app_arena_clear_event(void) {
  TSH_DECLARE;

  app_arena_t* arena = &g_app_arena;

  TSH_CHECK(arena->initialized, TS_ENOINIT);

  systask_id_t task_id = systask_id(systask_active());
  arena->tls[task_id].event_pending = false;

cleanup:
  TSH_RETURN;
}

// ---- app_arena event handling ----

static void on_task_created(void* context, systask_id_t task_id) {
  app_arena_t* arena = (app_arena_t*)context;

  if (!arena->initialized) {
    return;
  }

  // Just clear the TLS for the new task
  memset(&arena->tls[task_id], 0, sizeof(arena->tls[task_id]));
}

static void on_task_killed(void* context, systask_id_t task_id) {
  app_arena_t* arena = (app_arena_t*)context;

  if (!arena->initialized) {
    return;
  }

  for (size_t i = 0; i < ARRAY_LENGTH(arena->images); i++) {
    app_arena_entry_t* entry = &arena->images[i];
    if (entry->running && entry->applet.task.id == task_id) {
      // Mark the image as stopped
      entry->running = false;
      arena->task_killed = true;
      break;
    }
  }
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  app_arena_t* arena = (app_arena_t*)context;

  UNUSED(write_awaited);

  if (read_awaited) {
    syshandle_signal_read_ready(SYSHANDLE_APP_ARENA, &arena->task_killed);
    arena->task_killed = false;
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  app_arena_t* arena = (app_arena_t*)context;

  bool task_killed = *(bool*)param;
  if (task_killed) {
    arena->tls[task_id].event_pending = true;
  }

  return arena->tls[task_id].event_pending;
}

static const syshandle_vmt_t g_app_arena_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = on_task_killed,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
