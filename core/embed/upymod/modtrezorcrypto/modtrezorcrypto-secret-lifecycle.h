/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../secret_lifecycle.h"

#define SECRET_TASK_CAPACITY 64
MP_REGISTER_ROOT_POINTER(mp_obj_t secret_task_roots[SECRET_TASK_CAPACITY]);
typedef struct {
  uint32_t owner;
  bool root;
} secret_task_t;
static secret_task_t secret_tasks[SECRET_TASK_CAPACITY];

static int secret_task_find(mp_obj_t task) {
  for (size_t i = 0; i < SECRET_TASK_CAPACITY; i++)
    if (MP_STATE_VM(secret_task_roots)[i] == task) return i;
  return -1;
}
static void secret_tasks_forget(void) {
  memzero(secret_tasks, sizeof(secret_tasks));
  memzero(MP_STATE_VM(secret_task_roots),
          sizeof(MP_STATE_VM(secret_task_roots)));
}
/* Called before mp_init and before mp_deinit, including emulator soft restart.
 */
void trezorcrypto_secret_reset(void) {
  secret_revoke_all();
  secret_tasks_forget();
}

/// package: trezorcrypto.__init__
/// def _secret_task_register(task: Any, owner: SecretOwner | None) -> None:
///     """Bind a request root, or inherit the active request for a child."""
static mp_obj_t secret_task_register(mp_obj_t task, mp_obj_t owner) {
  if (secret_task_find(task) >= 0) return mp_const_none;
  uint32_t id = secret_owner;
  bool root = owner != mp_const_none;
  if (root) id = owner_object(owner)->id;
  if (!id && !root) return mp_const_none;
  secret_owner_t *o = secret_owner_find(id);
  if (!o || !o->parent)
    mp_raise_ValueError(MP_ERROR_TEXT("Expected live request owner"));
  for (size_t i = 0; i < SECRET_TASK_CAPACITY; i++) {
    if (MP_STATE_VM(secret_task_roots)[i] == MP_OBJ_NULL) {
      secret_tasks[i] = (secret_task_t){id, root};
      MP_STATE_VM(secret_task_roots)[i] = task;
      return mp_const_none;
    }
  }
  if (root) secret_owner_destroy(id);
  mp_raise_msg(&mp_type_MemoryError,
               MP_ERROR_TEXT("Secret task table exhausted"));
}
static MP_DEFINE_CONST_FUN_OBJ_2(secret_task_register_obj,
                                 secret_task_register);

/// def _secret_task_enter(task: Any) -> bool:
///     """Activate task ownership. False means the task has been revoked."""
static mp_obj_t secret_task_enter(mp_obj_t task) {
  secret_owner = 0;
  int i = secret_task_find(task);
  if (i >= 0) {
    if (!secret_owner_find(secret_tasks[i].owner)) return mp_const_false;
    secret_owner = secret_tasks[i].owner;
  }
  return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(secret_task_enter_obj, secret_task_enter);

/// def _secret_task_finish(task: Any) -> None:
///     """Revoke roots before callbacks; children release only their
///     binding."""
static mp_obj_t secret_task_finish(mp_obj_t task) {
  int i = secret_task_find(task);
  if (i >= 0) {
    if (secret_tasks[i].root) secret_owner_destroy(secret_tasks[i].owner);
    secret_tasks[i] = (secret_task_t){0};
    MP_STATE_VM(secret_task_roots)[i] = MP_OBJ_NULL;
  }
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(secret_task_finish_obj, secret_task_finish);

/// def _secret_tasks_clear() -> None:
///     """Erase request owners and forget tasks, preserving sessions."""
static mp_obj_t secret_tasks_clear(void) {
  secret_revoke_requests();
  secret_tasks_forget();
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(secret_tasks_clear_obj, secret_tasks_clear);
