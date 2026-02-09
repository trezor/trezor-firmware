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

#include <io/app_cache.h>
#include <io/app_loader.h>
#include <io/elf_loader.h>

#include "app_arena.h"

// Maximum number of tracked app loader entries
#define MAX_APP_LOADER_ENTRIES 1

typedef struct {
  // Application identifier (hash of the application image)
  app_hash_t hash;
  // Locked application image in the cache (or 0 if not used)
  app_cache_handle_t locked_image;
  // Applet associated with the application
  applet_t applet;
} app_entry_t;

typedef struct {
  // Indicates whether the app loader is initialized
  bool initialized;
  // Tracked app loader entries
  app_entry_t apps[MAX_APP_LOADER_ENTRIES];
} app_loader_t;

// Global app loader instance
static app_loader_t g_app_loader;

ts_t app_loader_init(void) {
  app_loader_t* loader = &g_app_loader;

  if (loader->initialized) {
    return TS_OK;
  }

  TSH_DECLARE;
  ts_t status;

  memset(loader, 0, sizeof(*loader));

  status = app_arena_init();
  TSH_CHECK_OK(status);

  loader->initialized = true;

cleanup:
  TSH_RETURN;
}

static app_entry_t* find_app_by_task(systask_id_t task_id) {
  app_loader_t* loader = &g_app_loader;

  for (size_t i = 0; i < MAX_APP_LOADER_ENTRIES; i++) {
    app_entry_t* entry = &loader->apps[i];
    if (entry->applet.task.id == task_id) {
      return entry;
    }
  }

  return NULL;
}

static app_entry_t* find_app_by_hash(const app_hash_t* hash) {
  app_loader_t* loader = &g_app_loader;

  for (size_t i = 0; i < MAX_APP_LOADER_ENTRIES; i++) {
    app_entry_t* entry = &loader->apps[i];
    if (memcmp(&entry->hash, hash, sizeof(app_hash_t)) == 0) {
      return entry;
    }
  }

  return NULL;
}

static app_entry_t* alloc_entry(const app_hash_t* hash) {
  app_loader_t* loader = &g_app_loader;

  app_hash_t zero_hash = {0};

  for (size_t i = 0; i < MAX_APP_LOADER_ENTRIES; i++) {
    app_entry_t* entry = &loader->apps[i];
    if (memcmp(&entry->hash, &zero_hash, sizeof(app_hash_t)) == 0) {
      memset(entry, 0, sizeof(app_entry_t));
      memcpy(&entry->hash, hash, sizeof(app_hash_t));
      return entry;
    }
  }

  return NULL;
}

static void remove_entry(app_entry_t* entry) {
  if (entry->locked_image != APP_CACHE_INVALID_HANDLE) {
    app_cache_unlock_image(entry->locked_image);
    entry->locked_image = APP_CACHE_INVALID_HANDLE;
  }

  memset(entry, 0, sizeof(*entry));
}

ts_t app_task_spawn(const app_hash_t* hash, systask_id_t* task_id) {
  app_loader_t* loader = &g_app_loader;

  TSH_DECLARE;
  ts_t status;

  app_entry_t* entry = NULL;

  TSH_CHECK(loader->initialized, TS_ENOINIT);

  // Check if the application is already spawned
  TSH_CHECK(find_app_by_hash(hash) == NULL, TS_EBUSY);

  entry = alloc_entry(hash);
  TSH_CHECK(entry != NULL, TS_ENOMEM);  // No space for new app entry

  void* image_ptr = NULL;
  size_t image_size = 0;

  entry->locked_image = app_cache_lock_image(hash, &image_ptr, &image_size);
  TSH_CHECK(entry->locked_image != APP_CACHE_INVALID_HANDLE, TS_ENOENT);

  status = elf_load(&entry->applet, image_ptr, image_size);

  if (ts_error(status)) {
    if (!ts_eq(status, TS_ENOMEM)) {
      // Remap to generic error
      status = TS_EINVAL;
    }
  }
  TSH_CHECK_OK(status);

  applet_run(&entry->applet);

  *task_id = entry->applet.task.id;

  TSH_RETURN;

cleanup:
  if (entry != NULL) {
    remove_entry(entry);
  }

  TSH_RETURN;
}

bool app_task_is_running(systask_id_t task_id) {
  app_loader_t* loader = &g_app_loader;

  if (!loader->initialized) {
    return false;
  }

  app_entry_t* entry = find_app_by_task(task_id);
  if (entry == NULL) {
    return false;
  }

  return systask_is_alive(&entry->applet.task);
}

ts_t app_task_get_pminfo(systask_id_t task_id, systask_postmortem_t* pminfo) {
  app_loader_t* loader = &g_app_loader;

  TSH_DECLARE;

  memset(pminfo, 0, sizeof(*pminfo));

  TSH_CHECK(loader->initialized, TS_ENOINIT);

  app_entry_t* entry = find_app_by_task(task_id);
  TSH_CHECK(entry != NULL, TS_ENOENT);

  *pminfo = entry->applet.task.pminfo;

cleanup:
  TSH_RETURN;
}

void app_task_unload(systask_id_t task_id) {
  app_loader_t* loader = &g_app_loader;

  if (!loader->initialized) {
    return;
  }

  app_entry_t* entry = find_app_by_task(task_id);
  if (entry != NULL) {
    applet_unload(&entry->applet);
    remove_entry(entry);
  }
}

#endif  // KERNEL_MODE
