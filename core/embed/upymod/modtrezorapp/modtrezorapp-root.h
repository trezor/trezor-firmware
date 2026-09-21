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

#include <py/obj.h>
#include <py/runtime.h>

#include <trezor_rtl.h>

#include <io/app_arena.h>

/// class AppRootState:
///     """
///     Represents the persisted state of root packets, including the minimum
///     timestamps for the three rings. The structure is opaque to MicroPython
///     and can be accessed only through its encoded representation, which can
///     be retrieved from or stored in persistent storage.
///     """
typedef struct {
  mp_obj_base_t base;
  app_root_state_t state;
} mp_obj_AppRootState_t;

// Version 1 of the AppRootState structure
typedef struct {
  // timestamp for the three rings (3 intentionally hardcoded for v1)
  int64_t timestamp[3];
} app_root_state_v1_t;

// Encoded representation of the AppRootState structure
typedef struct {
  // version of the encoded structure (v1 => 1)
  uint32_t version;
  uint32_t reserved;
  union {
    app_root_state_v1_t v1;
  } data;
} app_root_state_encoded_t;

// Encoded app_root_state_t size for v1
#define APP_ROOT_STATE_ENCODED_V1_SIZE \
  (offsetof(app_root_state_encoded_t, data) + sizeof(app_root_state_v1_t))

// Decodes the encoded representation of the AppRootState structure
static ts_t app_root_state_decode(app_root_state_t *state, const uint8_t *data,
                                  size_t data_size) {
  TSH_DECLARE;

  TSH_CHECK_ARG(state != NULL);
  TSH_CHECK_ARG(data != NULL);
  TSH_CHECK_ARG(data_size >= offsetof(app_root_state_encoded_t, data));
  TSH_CHECK_ARG(data_size <= sizeof(app_root_state_encoded_t));

  app_root_state_encoded_t encoded = {0};
  memcpy(&encoded, data, data_size);

  switch (encoded.version) {
    case 1:
      TSH_CHECK(data_size == APP_ROOT_STATE_ENCODED_V1_SIZE, TS_EBADMSG);

      state->ring_timestamp[0] = encoded.data.v1.timestamp[0];
      state->ring_timestamp[1] = encoded.data.v1.timestamp[1];
      state->ring_timestamp[2] = encoded.data.v1.timestamp[2];

      break;
    default:
      TSH_RAISE(TS_EBADMSG);
  }

cleanup:
  TSH_RETURN;
}

// Encodes the app_root_state_t structure into its encoded representation
static ts_t app_root_state_encode(const app_root_state_t *state, void *buffer,
                                  size_t buffer_size, size_t *encoded_size) {
  TSH_DECLARE;

  TSH_CHECK_ARG(state != NULL);
  TSH_CHECK_ARG(buffer != NULL);
  TSH_CHECK_ARG(encoded_size != NULL);
  TSH_CHECK_ARG(buffer_size >= sizeof(app_root_state_encoded_t));

  app_root_state_encoded_t encoded = {
      .version = 1,
      .data.v1.timestamp =
          {
              [0] = state->ring_timestamp[0],
              [1] = state->ring_timestamp[1],
              [2] = state->ring_timestamp[2],
          },
  };

  size_t size = APP_ROOT_STATE_ENCODED_V1_SIZE;
  memcpy(buffer, &encoded, size);
  *encoded_size = size;

cleanup:
  TSH_RETURN;
}

// clang-format off
/// def __init__(self, min_timestamp: int | None = None, state: bytes | None = None, /) -> None:
///     """
///     Creates an AppRootState object.
///     """
// clang-format on
static mp_obj_t mod_trezorapp_AppRootState_make_new(const mp_obj_type_t *type,
                                                    size_t n_args, size_t n_kw,
                                                    const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 2, false);
  mp_obj_AppRootState_t *o = mp_obj_malloc(mp_obj_AppRootState_t, type);

  memset(&o->state, 0, sizeof(app_root_state_t));

  // If a state is provided, deserialize it
  if (n_args >= 2 && args[1] != mp_const_none) {
    // deserialize the state from the provided bytes
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_READ);

    ts_t status = app_root_state_decode(&o->state, bufinfo.buf, bufinfo.len);
    if (ts_error(status)) {
      mp_raise_ValueError(MP_ERROR_TEXT("Failed to decode AppRootState"));
    }
  }

  // Apply the minimum timestamp to the ring timestamps
  if (n_args >= 1 && args[0] != mp_const_none) {
    int64_t min_timestamp = mp_obj_get_ll(args[0]);
    for (size_t i = 0; i < APP_RING_COUNT; i++) {
      o->state.ring_timestamp[i] =
          MAX(min_timestamp, o->state.ring_timestamp[i]);
    }
  }

  return MP_OBJ_FROM_PTR(o);
}

/// def serialize(self) -> bytes:
///     """
///     Serializes the AppRootState object to bytes.
///     """
static mp_obj_t mod_trezorapp_AppRootState_serialize(mp_obj_t self) {
  mp_obj_AppRootState_t *o = MP_OBJ_TO_PTR(self);

  app_root_state_encoded_t encoded_state;
  size_t encoded_size = 0;

  ts_t status =
      app_root_state_encode(&o->state, &encoded_state,
                            sizeof(app_root_state_encoded_t), &encoded_size);
  if (ts_error(status)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to encode AppRootState"));
  }

  return mp_obj_new_bytes((const byte *)&encoded_state, encoded_size);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorapp_AppRootState_serialize_obj,
                                 mod_trezorapp_AppRootState_serialize);

static const mp_rom_map_elem_t mod_trezorapp_AppRootState_locals_dict_table[] =
    {
        {MP_ROM_QSTR(MP_QSTR_serialize),
         MP_ROM_PTR(&mod_trezorapp_AppRootState_serialize_obj)},
};
static MP_DEFINE_CONST_DICT(mod_trezorapp_AppRootState_locals_dict,
                            mod_trezorapp_AppRootState_locals_dict_table);

// clang-format off
static MP_DEFINE_CONST_OBJ_TYPE(mod_trezorapp_AppRootState_type,
  MP_QSTR_AppRootState, MP_TYPE_FLAG_NONE,
  make_new, mod_trezorapp_AppRootState_make_new,
  locals_dict, &mod_trezorapp_AppRootState_locals_dict);
// clang-format on
