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
#include <util/app_loader.h>
#include <util/elf_loader.h>

#include "app_arena.h"

// Maximum number of tracked app loader entries
#define MAX_APP_LOADER_ENTRIES 1

typedef struct {
  // Application identifier (hash of the application image)
  app_hash_t hash;
  // Locked application image in the cache (or NULL if not used)
  app_cache_image_t* locked_image;
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

bool app_loader_init(void) {
  app_loader_t* loader = &g_app_loader;

  if (loader->initialized) {
    return true;
  }

  if (!app_arena_init()) {
    return false;
  }

  memset(loader, 0, sizeof(*loader));

  loader->initialized = true;
  return true;
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
  if (entry->locked_image != NULL) {
    app_cache_unlock_image(entry->locked_image);
    entry->locked_image = NULL;
  }

  memset(entry, 0, sizeof(*entry));
}

bool app_task_spawn(const app_hash_t* hash, systask_id_t* task_id) {
  app_loader_t* loader = &g_app_loader;

  if (!loader->initialized) {
    return false;
  }

  app_entry_t* entry = find_app_by_hash(hash);
  if (entry != NULL) {
    // Application is already spawned
    return false;
  }

  entry = alloc_entry(hash);
  if (entry == NULL) {
    // No space for new app entry
    return false;
  }

  void* image_ptr = NULL;
  size_t image_size = 0;

  entry->locked_image = app_cache_lock_image(hash, &image_ptr, &image_size);
  if (entry->locked_image == NULL) {
    // Unable to lock application image in cache
    remove_entry(entry);
    return false;
  }

  if (!elf_load(&entry->applet, image_ptr, image_size)) {
    remove_entry(entry);
    return false;
  }

  applet_run(&entry->applet);

  *task_id = entry->applet.task.id;

  return true;
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

bool app_task_get_pminfo(systask_id_t task_id, systask_postmortem_t* pminfo) {
  app_loader_t* loader = &g_app_loader;

  memset(pminfo, 0, sizeof(*pminfo));

  if (!loader->initialized) {
    return false;
  }

  app_entry_t* entry = find_app_by_task(task_id);
  if (entry == NULL) {
    return false;
  }

  *pminfo = entry->applet.task.pminfo;
  return true;
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
