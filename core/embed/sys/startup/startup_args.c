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

#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/startup_args.h>

// Version of the startup_args_t structure used in this implementation.
// This should be incremented whenever the structure changes.
#define STARTUP_ARGS_VERSION_V1 1

// Maximum size of the output buffer for startup arguments.
#define STARTUP_ARGS_BUFFER_SIZE 4096

// Size of the startup_args_t header
#define STARTUP_ARGS_HEADER_SIZE offsetof(startup_args_t, data)

// Alignment requirement for individual argument entries in the buffer.
#define ARG_ENTRY_ALIGNMENT 4

// Calculates the total size of an argument entry in the buffer,
// including padding for alignment.
#define ARG_ENTRY_SIZE(value_size) \
  ALIGN_UP(sizeof(arg_entry_t) + (value_size), ARG_ENTRY_ALIGNMENT)

// Initial offset for the first argument entry in the buffer, accounting for
// the startup_args_t header and alignment. Should evaluate to zero if the
// header size is already aligned.
#define ARG_ENTRY_INITIAL_OFFSET                             \
  (ALIGN_UP(STARTUP_ARGS_HEADER_SIZE, ARG_ENTRY_ALIGNMENT) - \
   STARTUP_ARGS_HEADER_SIZE)

// Output buffer for startup arguments, populated with `startup_args_add()` and
// retrieved with `startup_args_export()`.
static struct {
  startup_args_t header;
  uint8_t buffer[STARTUP_ARGS_BUFFER_SIZE];
} g_args_buffer;

// Pointer to the current output arguments structure, initialized on the first
// call to `startup_args_add()`. If `startup_args_add()` is not called at all,
// this will remain NULL and the output buffer and `g_args_buffer`
// will be optimized out by the linker.
static startup_args_t* g_args_out_ptr;

// Flag indicating whether there is a pending reservation that has not
// been committed yet.
static bool g_reservation_pending = false;

// Input arguments passed from the previous stage, initialized with
// `startup_args_import()` and accessed with `startup_args_get()`.
static const startup_args_t* g_args_in;

// Internal structure of an individual argument entry in the input/output
// buffer.
typedef struct {
  uint16_t type;
  uint16_t size;
  uint8_t value[0];
} arg_entry_t;

// forward declaration
static const arg_entry_t* find_entry(const startup_args_t* args,
                                     startup_args_type_t type);

ts_t startup_args_add(startup_args_type_t type, const void* value,
                      size_t size) {
  TSH_DECLARE;

  void* dest = NULL;

  TSH_CHECK_ARG(size == 0 || value != NULL);

  ts_t status = startup_args_reserve(type, size, &dest);
  TSH_CHECK_OK(status);

  if (size > 0) {
    memcpy(dest, value, size);
  }

  startup_args_commit(size);

cleanup:
  TSH_RETURN;
}

ts_t startup_args_reserve(startup_args_type_t type, size_t size,
                          void** buffer) {
  TSH_DECLARE;

  *buffer = NULL;

  TSH_CHECK_ARG(size <= UINT16_MAX);
  TSH_CHECK_ARG(type != STARTUP_ARGS_TYPE_INVALID);

  TSH_CHECK(!g_reservation_pending, TS_EBUSY);

  startup_args_t* args = g_args_out_ptr;

  if (args == NULL) {
    // First call to `startup_args_add()`, initialize the output buffer header.
    args = &g_args_buffer.header;
    args->version = STARTUP_ARGS_VERSION_V1;
    args->size = ARG_ENTRY_INITIAL_OFFSET;
    g_args_out_ptr = args;
  }

  TSH_CHECK(find_entry(args, type) == NULL, TS_EEXIST);

  uint32_t entry_size = ARG_ENTRY_SIZE(size);
  TSH_CHECK(args->size + entry_size <= STARTUP_ARGS_BUFFER_SIZE, TS_ENOMEM);

  arg_entry_t* entry = (arg_entry_t*)(args->data + args->size);
  entry->type = type;
  entry->size = size;

  if (size > 0) {
    // Zero out the reserved space for the argument value
    memset(entry->value, 0, size);
  }

  *buffer = entry->value;

  g_reservation_pending = true;

cleanup:
  TSH_RETURN;
}

ts_t startup_args_commit(size_t size) {
  TSH_DECLARE;

  startup_args_t* args = g_args_out_ptr;

  TSH_CHECK(g_reservation_pending, TS_EINVAL);
  TSH_CHECK(args != NULL, TS_EINVAL);

  arg_entry_t* entry = (arg_entry_t*)(args->data + args->size);

  TSH_CHECK(entry->size >= size, TS_EINVAL);

  entry->size = size;
  args->size += ARG_ENTRY_SIZE(size);

  g_reservation_pending = false;

cleanup:
  TSH_RETURN;
}

void startup_args_discard(void) { g_reservation_pending = false; }

const startup_args_t* startup_args_export(void) { return g_args_out_ptr; }

ts_t startup_args_import(const startup_args_t* args) {
  TSH_DECLARE;

  TSH_CHECK_ARG(args == NULL || args->version == STARTUP_ARGS_VERSION_V1);

  g_args_in = args;

cleanup:
  TSH_RETURN;
}

ts_t startup_args_get(startup_args_type_t type, const void** value,
                      size_t* size) {
  TSH_DECLARE;

  const startup_args_t* args = g_args_in;

  TSH_CHECK(args != NULL, TS_ENOINIT);
  TSH_CHECK_ARG(type != STARTUP_ARGS_TYPE_INVALID);

  const arg_entry_t* entry = find_entry(args, type);

  if (value != NULL) {
    *value = entry != NULL ? entry->value : NULL;
  }

  if (size != NULL) {
    *size = entry != NULL ? entry->size : 0;
  }

  TSH_CHECK(entry != NULL, TS_ENOENT);

cleanup:
  TSH_RETURN;
}

// Finds the argument entry with the specified type in the given arguments
static const arg_entry_t* find_entry(const startup_args_t* args,
                                     startup_args_type_t type) {
  uintptr_t offset = ARG_ENTRY_INITIAL_OFFSET;

  while (offset + sizeof(arg_entry_t) <= args->size) {
    const arg_entry_t* entry = (const arg_entry_t*)(args->data + offset);

    if (offset + ARG_ENTRY_SIZE(0) > args->size) {
      // Malformed buffer, entry header size exceeds total size
      break;
    }

    offset += ARG_ENTRY_SIZE(entry->size);

    if (offset > args->size) {
      // Malformed buffer, entry total size exceeds total size
      break;
    }

    if (entry->type == type) {
      return entry;
    }
  }

  return NULL;
}
