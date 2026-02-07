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

#include <trezor_rtl.h>

#include <io/app_cache.h>

#include "app_arena.h"

// Maximum number of tracked app cache entries
#define MAX_APP_CACHE_ENTRIES 1

typedef struct {
  // Application identifier (hash of the application image)
  app_hash_t hash;
  // Application is locked, preventing deletion
  bool locked;
  // Application image is being loaded
  bool loading;
  // Allocated space for the application image
  void* image_data;
  // Allocated size of the application image
  size_t image_size;
} app_cache_image_t;

typedef struct {
  // Indicates whether the app cache is initialized
  bool initialized;
  // Tracked app cache entries
  app_cache_image_t apps[MAX_APP_CACHE_ENTRIES];
} app_cache_t;

// Global app cache instance
static app_cache_t g_app_cache;

ts_t app_cache_init(void) {
  app_cache_t* cache = &g_app_cache;

  if (cache->initialized) {
    return TS_OK;
  }

  TSH_DECLARE;
  ts_t status;

  memset(cache, 0, sizeof(*cache));

  status = app_arena_init();
  TSH_CHECK_OK(status);

  cache->initialized = true;

cleanup:
  TSH_RETURN;
}

static app_cache_image_t* find_entry_by_hash(const app_hash_t* hash) {
  app_cache_t* cache = &g_app_cache;

  for (size_t i = 0; i < MAX_APP_CACHE_ENTRIES; i++) {
    app_cache_image_t* image = &cache->apps[i];
    if (memcmp(&image->hash, hash, sizeof(app_hash_t)) == 0) {
      return image;
    }
  }

  return NULL;
}

static app_cache_image_t* validate_image_handle(app_cache_handle_t handle) {
  app_cache_t* cache = &g_app_cache;

  if (!cache->initialized) {
    return NULL;
  }

  for (size_t i = 0; i < MAX_APP_CACHE_ENTRIES; i++) {
    app_cache_image_t* image = &cache->apps[i];
    if (image == (app_cache_image_t*)handle) {
      return image;
    }
  }

  return NULL;
}

static inline app_cache_handle_t image_to_handle(app_cache_image_t* image) {
  return (app_cache_handle_t)image;
}

static app_cache_image_t* alloc_entry(const app_hash_t* hash) {
  app_cache_t* cache = &g_app_cache;

  app_hash_t zero_hash = {0};

  for (size_t i = 0; i < MAX_APP_CACHE_ENTRIES; i++) {
    app_cache_image_t* image = &cache->apps[i];
    if (memcmp(&image->hash, &zero_hash, sizeof(app_hash_t)) == 0) {
      memcpy(&image->hash, hash, sizeof(app_hash_t));
      return image;
    }
  }

  return NULL;
}

static void remove_entry(app_cache_image_t* image) {
  if (image->image_data != NULL) {
    app_arena_free(image->image_data);
  }
  memset(image, 0, sizeof(*image));
}

static void reclaim_free_space(size_t size) {
  app_cache_t* cache = &g_app_cache;

  // basic implementation: remove all non-locked entries
  for (size_t i = 0; i < MAX_APP_CACHE_ENTRIES; i++) {
    app_cache_image_t* image = &cache->apps[i];
    if (!image->locked) {
      remove_entry(image);
    }
  }
}

app_cache_handle_t app_cache_create_image(const app_hash_t* hash, size_t size) {
  app_cache_t* cache = &g_app_cache;

  if (!cache->initialized) {
    return APP_CACHE_INVALID_HANDLE;
  }

  app_cache_image_t* image = find_entry_by_hash(hash);
  if (image != NULL) {
    if (image->loading || image->locked) {
      // Image is already being used
      return APP_CACHE_INVALID_HANDLE;
    }

    // Remove existing image to create a new one
    remove_entry(image);
  }

  reclaim_free_space(size);

  image = alloc_entry(hash);
  if (image == NULL) {
    // No space for new app image
    return APP_CACHE_INVALID_HANDLE;
  }

  image->image_data = app_arena_alloc(size, APP_ALLOC_IMAGE);
  image->image_size = size;
  image->loading = true;

  if (image->image_data == NULL) {
    // Allocation failed, invalidate the image
    remove_entry(image);
    return APP_CACHE_INVALID_HANDLE;
  }

  return image_to_handle(image);
}

ts_t app_cache_write_image(app_cache_handle_t handle, uintptr_t offset,
                           const void* data, size_t size) {
  app_cache_t* cache = &g_app_cache;

  TSH_DECLARE;

  TSH_CHECK(cache->initialized, TS_ENOINIT);

  app_cache_image_t* image = validate_image_handle(handle);

  // Check whether the image exists and can be written to
  TSH_CHECK(image != NULL, TS_ENOENT);
  TSH_CHECK(image->loading, TS_EBUSY);

  // Check whether the image data is allocated
  TSH_CHECK(image->image_data != NULL, TS_EINVAL);

  // Check whether the offset and size are within bounds
  TSH_CHECK(offset < image->image_size, TS_EINVAL);
  TSH_CHECK(size <= image->image_size - offset, TS_EINVAL);

  // TODO: Consider a special new mpu mode or reusing MPU_MODE_APP here
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DISABLED);
  memcpy((uint8_t*)image->image_data + offset, data, size);
  mpu_restore(mpu_mode);

cleanup:
  TSH_RETURN;
}

ts_t app_cache_finalize_image(app_cache_handle_t handle, bool accept) {
  app_cache_t* cache = &g_app_cache;

  TSH_DECLARE;

  TSH_CHECK(cache->initialized, TS_ENOINIT);

  app_cache_image_t* image = validate_image_handle(handle);
  TSH_CHECK(image != NULL, TS_ENOENT);
  TSH_CHECK(image->loading, TS_EINVAL);

  if (accept) {
    image->loading = false;
  } else {
    remove_entry(image);
  }

cleanup:
  TSH_RETURN;
}

app_cache_handle_t app_cache_lock_image(const app_hash_t* hash, void** ptr,
                                        size_t* size) {
  app_cache_t* cache = &g_app_cache;

  *ptr = NULL;
  *size = 0;

  if (!cache->initialized) {
    return APP_CACHE_INVALID_HANDLE;
  }

  app_cache_image_t* image = find_entry_by_hash(hash);
  if (image == NULL || image->locked || image->loading) {
    return APP_CACHE_INVALID_HANDLE;
  }

  image->locked = true;

  *ptr = image->image_data;
  *size = image->image_size;
  return image_to_handle(image);
}

void app_cache_unlock_image(app_cache_handle_t handle) {
  app_cache_t* cache = &g_app_cache;

  if (!cache->initialized) {
    return;
  }

  app_cache_image_t* image = validate_image_handle(handle);

  if (image != NULL) {
    image->locked = false;
  }
}

#ifdef TREZOR_EMULATOR
ts_t app_cache_load_file(const app_hash_t* hash, const char* filename) {
  TSH_DECLARE;
  ts_t status;

  app_cache_handle_t image = APP_CACHE_INVALID_HANDLE;

  FILE* f = fopen(filename, "rb");
  TSH_CHECK(f != NULL, TS_EIO);

  fseek(f, 0, SEEK_END);
  size_t size = ftell(f);
  fseek(f, 0, SEEK_SET);

  image = app_cache_create_image(hash, size);
  TSH_CHECK(image != APP_CACHE_INVALID_HANDLE, TS_ENOMEM);

  uintptr_t offset = 0;

  while (size > 0) {
    uint8_t buffer[1024];
    size_t to_read = size < sizeof(buffer) ? size : sizeof(buffer);

    size_t read = fread(buffer, 1, to_read, f);
    TSH_CHECK(read == to_read, TS_EIO);

    status = app_cache_write_image(image, offset, buffer, read);
    TSH_CHECK_OK(status);

    offset += read;
    size -= read;
  }

  fclose(f);
  f = NULL;

  status = app_cache_finalize_image(image, true);
  TSH_CHECK_OK(status);

  image = APP_CACHE_INVALID_HANDLE;

cleanup:
  if (f != NULL) {
    fclose(f);
  }

  if (image != APP_CACHE_INVALID_HANDLE) {
    status = app_cache_finalize_image(image, false);
    UNUSED(status);
  }

  TSH_RETURN;
}

#endif

#endif  // KERNEL_MODE
