/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_MOD_SECBYTES_H
#define TREZOR_MOD_SECBYTES_H
#include "../secret_lifecycle.h"
#include "secret_store.h"

/// package: trezorcrypto.__init__
/// class secbytes:
///     """Opaque immutable native secret. No buffer or plaintext interface."""
/// def __init__(self, value: AnyBytes | None, capacity: int = 160) -> None:
///     """Copy existing plaintext; this does not erase its Python source.
///     None makes an empty holder for a long-lived slot, see take().
///     capacity limits an empty holder; populated values use their actual
///     size."""
/// def destroy(self) -> None:
///     """Erase this value. Idempotent."""
/// def take(self, other: secbytes) -> None:
///     """Erase this value, then move other's secret into this object, leaving
///     other empty. Lets long-lived holders change value without allocating.
///     An oversized move raises ValueError and leaves both values unchanged;
///     populated objects have capacity equal to their initial secret length."""
/// def empty(self) -> bool:
///     """Return whether this object holds no secret (local check only)."""
typedef struct {
  mp_obj_base_t base;
  size_t capacity;
  uint8_t blob[];
} mp_obj_secbytes_t;
extern const mp_obj_type_t mod_trezorcrypto_secbytes_type;

static void vault_raise(vault_request_t *r, vault_response_t *out) {
  if (!secret_rpc(r, out))
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid or locked vault"));
}
/* Only ciphertext lives in this allocation. capacity survives destruction so
 * finalization and moves always wipe exactly the allocated storage. */
static size_t secbytes_storage_size(const mp_obj_secbytes_t *o) {
  return vault_bytes_blob_size(o->capacity);
}
static void secbytes_clear(mp_obj_secbytes_t *o) {
  memzero(o->blob, secbytes_storage_size(o));
}
static mp_obj_secbytes_t *secbytes_new(size_t capacity) {
  mp_obj_secbytes_t *o = mp_obj_malloc_var_with_finaliser(
      mp_obj_secbytes_t, blob, uint8_t, vault_bytes_blob_size(capacity),
      &mod_trezorcrypto_secbytes_type);
  o->capacity = capacity;
  secbytes_clear(o);
  return o;
}
static vault_blob_t secbytes_blob(const mp_obj_secbytes_t *o) {
  vault_blob_t blob = {0};
  memcpy(blob.bytes, o->blob, secbytes_storage_size(o));
  return blob;
}
static void secbytes_set_blob(mp_obj_secbytes_t *o, const vault_blob_t *blob) {
  memcpy(o->blob, blob->bytes, secbytes_storage_size(o));
}
static mp_obj_t secbytes_copy(const void *data, size_t len) {
  if (len > SECRET_STORE_BYTES)
    mp_raise_ValueError(MP_ERROR_TEXT("Secret too long"));
  mp_obj_secbytes_t *o = secbytes_new(len);
  vault_request_t r = {.op = VAULT_IMPORT_BYTES, .length = len};
  vault_response_t out = {0};
  memcpy(r.data, data, len);
  vault_raise(&r, &out);
  secbytes_set_blob(o, &out.blob);
  return MP_OBJ_FROM_PTR(o);
}
static mp_obj_t secbytes_make_new(const mp_obj_type_t *type, size_t n_args,
                                  size_t n_kw, const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 1, 2, false);
  if (args[0] == mp_const_none) {
    mp_int_t capacity =
        n_args > 1 ? mp_obj_get_int(args[1]) : VAULT_SECRET_SIZE;
    if (capacity < 0 || capacity > VAULT_SECRET_SIZE)
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid secret capacity"));
    return MP_OBJ_FROM_PTR(secbytes_new(capacity));
  }
  if (n_args > 1)
    mp_raise_TypeError(MP_ERROR_TEXT("Capacity requires empty holder"));
  mp_buffer_info_t b = {0};
  mp_get_buffer_raise(args[0], &b, MP_BUFFER_READ);
  return secbytes_copy(b.buf, b.len);
}
static mp_obj_secbytes_t *secbytes_object(mp_obj_t obj) {
  if (!mp_obj_is_type(obj, &mod_trezorcrypto_secbytes_type))
    mp_raise_TypeError(MP_ERROR_TEXT("Expected secbytes"));
  return MP_OBJ_TO_PTR(obj);
}
static mp_obj_t secbytes_destroy(mp_obj_t self) {
  secbytes_clear(secbytes_object(self));
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(secbytes_destroy_obj, secbytes_destroy);
static mp_obj_t secbytes_take(mp_obj_t self, mp_obj_t other) {
  mp_obj_secbytes_t *o = secbytes_object(self);
  mp_obj_secbytes_t *src = secbytes_object(other);
  if (o == src) return mp_const_none;
  /* Check before wiping either value: an oversized move leaves both intact. */
  size_t length = src->blob[5];
  if (length > o->capacity)
    mp_raise_ValueError(MP_ERROR_TEXT("Secret exceeds holder capacity"));
  secbytes_clear(o);
  memcpy(o->blob, src->blob, vault_bytes_blob_size(length));
  secbytes_clear(src);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(secbytes_take_obj, secbytes_take);
static mp_obj_t secbytes_empty(mp_obj_t self) {
  mp_obj_secbytes_t *o = secbytes_object(self);
  for (size_t i = 0; i < secbytes_storage_size(o); i++)
    if (o->blob[i]) return mp_const_false;
  return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(secbytes_empty_obj, secbytes_empty);
static void secbytes_print(const mp_print_t *print, mp_obj_t self,
                           mp_print_kind_t kind) {
  mp_print_str(print, "<secbytes>");
}
static const mp_rom_map_elem_t secbytes_locals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_destroy), MP_ROM_PTR(&secbytes_destroy_obj)},
    {MP_ROM_QSTR(MP_QSTR_take), MP_ROM_PTR(&secbytes_take_obj)},
    {MP_ROM_QSTR(MP_QSTR_empty), MP_ROM_PTR(&secbytes_empty_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&secbytes_destroy_obj)},
};
static MP_DEFINE_CONST_DICT(secbytes_locals, secbytes_locals_table);
MP_DEFINE_CONST_OBJ_TYPE(mod_trezorcrypto_secbytes_type, MP_QSTR_secbytes,
                         MP_TYPE_FLAG_NONE, make_new, secbytes_make_new, print,
                         secbytes_print, locals_dict, &secbytes_locals);

/// mock:global
/// def authorize_locked_session(authorized: bool) -> None:
///     """Grant/revoke the current session's confirmed CoinJoin permission.
///     Granting requires unlocked storage and a live request."""
static mp_obj_t authorize_locked_session(mp_obj_t authorized) {
  vault_request_t r = {.op = VAULT_AUTHORIZE_LOCKED,
                       .arg = mp_obj_is_true(authorized)};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(authorize_locked_session_obj,
                                 authorize_locked_session);

/// def begin_preauthorized_request() -> None:
///     """Delegate a confirmed CoinJoin session grant to this request. It
///     survives consuming the last round until this request is torn down."""
static mp_obj_t begin_preauthorized_request(void) {
  vault_request_t r = {.op = VAULT_AUTHORIZE_LOCKED, .arg = 2};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(begin_preauthorized_request_obj,
                                 begin_preauthorized_request);

/// def begin_confirmed_request() -> None:
///     """Allow this confirmed request's crypto to finish after autolock.
///     A new grant requires unlocked storage and does not authorize a
///     session."""
static mp_obj_t begin_confirmed_request(void) {
  vault_request_t r = {.op = VAULT_AUTHORIZE_LOCKED, .arg = 3};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(begin_confirmed_request_obj,
                                 begin_confirmed_request);

/// def revoke_secrets() -> None:
///     """Erase all native owners and entries; emergency teardown only."""
static mp_obj_t revoke_secrets(void) {
  trezorcrypto_secret_reset();
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(revoke_secrets_obj, revoke_secrets);

/* Pack SLIP-0021 labels as length-prefixed strings for VAULT_SLIP21. */
static void slip21_request(vault_request_t *r, mp_obj_t source, mp_obj_t path,
                           uint32_t arg) {
  size_t count = 0;
  mp_obj_t *labels = NULL;
  mp_obj_get_array(path, &count, &labels);
  *r = (vault_request_t){.op = VAULT_SLIP21,
                         .blob = secbytes_blob(secbytes_object(source)),
                         .arg = arg};
  for (size_t i = 0; i < count; i++) {
    mp_buffer_info_t label = {0};
    mp_get_buffer_raise(labels[i], &label, MP_BUFFER_READ);
    if (label.len > 255 || label.len + 1 > VAULT_DATA_SIZE - r->length)
      mp_raise_ValueError(MP_ERROR_TEXT("SLIP-21 path too long"));
    r->data[r->length++] = label.len;
    memcpy(r->data + r->length, label.buf, label.len);
    r->length += label.len;
  }
}

/// def slip21_derive(
///     source: secbytes,
///     path: Sequence[AnyBytes],
///     root: bool = False,
///     key: bool = False,
/// ) -> secbytes:
///     """SLIP-0021 in the vault: derive from a seed (root) or a 64-byte node
///     along path. Return the sealed node or, with key, its sealed key."""
static mp_obj_t slip21_derive(size_t n_args, const mp_obj_t *pos,
                              mp_map_t *kw) {
  enum { ARG_source, ARG_path, ARG_root, ARG_key };
  static const mp_arg_t allowed[] = {
      {MP_QSTR_source, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none}},
      {MP_QSTR_path, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = mp_const_none}},
      {MP_QSTR_root, MP_ARG_BOOL, {.u_bool = false}},
      {MP_QSTR_key, MP_ARG_BOOL, {.u_bool = false}},
  };
  mp_arg_val_t args[MP_ARRAY_SIZE(allowed)];
  mp_arg_parse_all(n_args, pos, kw, MP_ARRAY_SIZE(allowed), allowed, args);
  bool key = args[ARG_key].u_bool;
  mp_obj_secbytes_t *value = secbytes_new(key ? 32 : 64);
  vault_request_t r;
  slip21_request(&r, args[ARG_source].u_obj, args[ARG_path].u_obj,
                 (args[ARG_root].u_bool ? VAULT_SLIP21_ROOT : 0) |
                     (key ? VAULT_SLIP21_KEY : VAULT_SLIP21_NODE));
  vault_response_t out = {0};
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(slip21_derive_obj, 2, slip21_derive);

/// def slip21_export(seed: secbytes, path: Sequence[AnyBytes]) -> bytes:
///     """Return a SLIP-0021 node in plaintext, for protocols that hand it to
///     the host. The kernel allows only the Evolu namespace."""
static mp_obj_t slip21_export(mp_obj_t seed, mp_obj_t path) {
  vault_request_t r;
  slip21_request(&r, seed, path, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT);
  vault_response_t out = {0};
  vault_raise(&r, &out);
  mp_obj_t node = mp_obj_new_bytes(out.signature, 64);
  memzero(&out, sizeof(out));
  return node;
}
static MP_DEFINE_CONST_FUN_OBJ_2(slip21_export_obj, slip21_export);

/// class SecretOwner:
///     """Explicit native session owner, or request owner beneath a session."""
/// def __init__(
///     self, parent: SecretOwner | None = None, bound: bool = True
/// ) -> None:
///     """Allocate a bounded, generation-checked owner identity. With
///     bound=False, make an unbound holder for a long-lived slot, see renew().
///     """
/// def destroy(self) -> None:
///     """Erase this owner and its descendants without allocating."""
/// def renew(self, parent: SecretOwner | None = None) -> None:
///     """Erase the current identity and bind a fresh one in place, so a
///     long-lived holder never needs a new heap object."""
/// def valid(self) -> bool:
///     """Return whether this owner is still live."""
typedef struct {
  mp_obj_base_t base;
  uint32_t id;
} mp_obj_secret_owner_t;
extern const mp_obj_type_t mod_trezorcrypto_SecretOwner_type;
static mp_obj_secret_owner_t *owner_object(mp_obj_t obj) {
  if (!mp_obj_is_type(obj, &mod_trezorcrypto_SecretOwner_type))
    mp_raise_TypeError(MP_ERROR_TEXT("Expected SecretOwner"));
  return MP_OBJ_TO_PTR(obj);
}
static uint32_t owner_create_raise(mp_obj_t parent_obj) {
  uint32_t parent = 0;
  if (parent_obj != mp_const_none) {
    parent = owner_object(parent_obj)->id;
    if (!secret_owner_find(parent))
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid parent owner"));
  }
  uint32_t id = secret_owner_create(parent);
  if (!id)
    mp_raise_msg(&mp_type_MemoryError,
                 MP_ERROR_TEXT("Secret owners exhausted"));
  return id;
}
static mp_obj_t owner_make_new(const mp_obj_type_t *type, size_t n_args,
                               size_t n_kw, const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 2, false);
  mp_obj_t parent = n_args ? args[0] : mp_const_none;
  bool bound = n_args < 2 || mp_obj_is_true(args[1]);
  if (!bound && parent != mp_const_none)
    mp_raise_ValueError(MP_ERROR_TEXT("Unbound owner takes no parent"));
  /* Allocate the wrapper first: a Python allocation failure must not leave
   * an unreachable live native owner behind. */
  mp_obj_secret_owner_t *o = mp_obj_malloc(mp_obj_secret_owner_t, type);
  o->id = 0;
  if (bound) o->id = owner_create_raise(parent);
  return MP_OBJ_FROM_PTR(o);
}
static mp_obj_t owner_destroy(mp_obj_t self) {
  secret_owner_destroy(owner_object(self)->id);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(owner_destroy_obj, owner_destroy);
static mp_obj_t owner_renew(size_t n_args, const mp_obj_t *args) {
  mp_obj_secret_owner_t *o = owner_object(args[0]);
  mp_obj_t parent = n_args > 1 ? args[1] : mp_const_none;
  if (parent == args[0])
    mp_raise_ValueError(MP_ERROR_TEXT("Owner cannot be its own parent"));
  /* Resolve the parent before erasing, so a failed renew keeps nothing. */
  if (parent != mp_const_none) owner_object(parent);
  secret_owner_destroy(o->id);
  o->id = 0;
  o->id = owner_create_raise(parent);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(owner_renew_obj, 1, 2, owner_renew);
static mp_obj_t owner_valid(mp_obj_t self) {
  return mp_obj_new_bool(secret_owner_find(owner_object(self)->id) != NULL);
}
static MP_DEFINE_CONST_FUN_OBJ_1(owner_valid_obj, owner_valid);
static const mp_rom_map_elem_t owner_locals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_destroy), MP_ROM_PTR(&owner_destroy_obj)},
    {MP_ROM_QSTR(MP_QSTR_renew), MP_ROM_PTR(&owner_renew_obj)},
    {MP_ROM_QSTR(MP_QSTR_valid), MP_ROM_PTR(&owner_valid_obj)},
};
static MP_DEFINE_CONST_DICT(owner_locals, owner_locals_table);
MP_DEFINE_CONST_OBJ_TYPE(mod_trezorcrypto_SecretOwner_type, MP_QSTR_SecretOwner,
                         MP_TYPE_FLAG_NONE, make_new, owner_make_new,
                         locals_dict, &owner_locals);

/// mock:global
/// def _secret_owner_activate(owner: SecretOwner | None) -> None:
///     """Scheduler hook; None disables secret operations. Lifetime only, not
///     isolation."""
static mp_obj_t owner_activate(mp_obj_t obj) {
  secret_owner = 0;
  if (obj != mp_const_none) {
    uint32_t id = owner_object(obj)->id;
    if (!secret_owner_find(id))
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid secret owner"));
    secret_owner = id;
  }
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(owner_activate_obj, owner_activate);

#endif
