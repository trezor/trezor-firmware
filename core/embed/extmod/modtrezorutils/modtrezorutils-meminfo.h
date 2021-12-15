/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#if !TREZOR_EMULATOR || PYOPT
#define MEMINFO_DICT_ENTRIES /* empty */

#else

#include "py/bc.h"
#include "py/gc.h"
#include "py/nlr.h"
#include "py/objarray.h"
#include "py/objfun.h"
#include "py/objgenerator.h"
#include "py/objlist.h"
#include "py/objstr.h"
#include "py/objtype.h"

#include "embed/extmod/trezorobj.h"
#include "embed/rust/librust.h"
#include "embed/trezorhal/usb.h"

#include <string.h>

#define WORDS_PER_BLOCK ((MICROPY_BYTES_PER_GC_BLOCK) / MP_BYTES_PER_OBJ_WORD)
#define BYTES_PER_BLOCK (MICROPY_BYTES_PER_GC_BLOCK)

// ATB = allocation table byte
// 0b00 = FREE -- free block
// 0b01 = HEAD -- head of a chain of blocks
// 0b10 = TAIL -- in the tail of a chain of blocks
// 0b11 = MARK -- marked head block

#define AT_FREE (0)
#define AT_HEAD (1)
#define AT_TAIL (2)
#define AT_MARK (3)

#define BLOCKS_PER_ATB (4)
#define ATB_MASK_0 (0x03)
#define ATB_MASK_1 (0x0c)
#define ATB_MASK_2 (0x30)
#define ATB_MASK_3 (0xc0)

#define ATB_0_IS_FREE(a) (((a)&ATB_MASK_0) == 0)
#define ATB_1_IS_FREE(a) (((a)&ATB_MASK_1) == 0)
#define ATB_2_IS_FREE(a) (((a)&ATB_MASK_2) == 0)
#define ATB_3_IS_FREE(a) (((a)&ATB_MASK_3) == 0)

#define BLOCK_SHIFT(block) (2 * ((block) & (BLOCKS_PER_ATB - 1)))
#define ATB_GET_KIND(block)                                         \
  ((MP_STATE_MEM(gc_alloc_table_start)[(block) / BLOCKS_PER_ATB] >> \
    BLOCK_SHIFT(block)) &                                           \
   3)
#define ATB_ANY_TO_FREE(block)                                        \
  do {                                                                \
    MP_STATE_MEM(gc_alloc_table_start)                                \
    [(block) / BLOCKS_PER_ATB] &= (~(AT_MARK << BLOCK_SHIFT(block))); \
  } while (0)
#define ATB_FREE_TO_HEAD(block)                                    \
  do {                                                             \
    MP_STATE_MEM(gc_alloc_table_start)                             \
    [(block) / BLOCKS_PER_ATB] |= (AT_HEAD << BLOCK_SHIFT(block)); \
  } while (0)
#define ATB_FREE_TO_TAIL(block)                                    \
  do {                                                             \
    MP_STATE_MEM(gc_alloc_table_start)                             \
    [(block) / BLOCKS_PER_ATB] |= (AT_TAIL << BLOCK_SHIFT(block)); \
  } while (0)
#define ATB_HEAD_TO_MARK(block)                                    \
  do {                                                             \
    MP_STATE_MEM(gc_alloc_table_start)                             \
    [(block) / BLOCKS_PER_ATB] |= (AT_MARK << BLOCK_SHIFT(block)); \
  } while (0)
#define ATB_MARK_TO_HEAD(block)                                       \
  do {                                                                \
    MP_STATE_MEM(gc_alloc_table_start)                                \
    [(block) / BLOCKS_PER_ATB] &= (~(AT_TAIL << BLOCK_SHIFT(block))); \
  } while (0)

#define BLOCK_FROM_PTR(ptr) \
  (((byte *)(ptr)-MP_STATE_MEM(gc_pool_start)) / BYTES_PER_BLOCK)
#define PTR_FROM_BLOCK(block) \
  (((block)*BYTES_PER_BLOCK + (uintptr_t)MP_STATE_MEM(gc_pool_start)))
#define ATB_FROM_BLOCK(bl) ((bl) / BLOCKS_PER_ATB)

// ptr should be of type void*
#define VERIFY_PTR(ptr)                                                       \
  (((uintptr_t)(ptr) & (BYTES_PER_BLOCK - 1)) ==                              \
       0 /* must be aligned on a block */                                     \
   && ptr >= (void *)MP_STATE_MEM(                                            \
                 gc_pool_start) /* must be above start of pool */             \
   && ptr < (void *)MP_STATE_MEM(gc_pool_end) /* must be below end of pool */ \
  )

#define Q_GET_DATA(q) \
  ((q) + MICROPY_QSTR_BYTES_IN_HASH + MICROPY_QSTR_BYTES_IN_LEN)
extern const qstr_pool_t mp_qstr_const_pool;

size_t find_allocated_size(void const *const ptr) {
  if (!ptr) {
    return 0;
  }

  if (!VERIFY_PTR(ptr)) {
    // printf("failed to verify ptr: %p\n", ptr);
    return 0;
  }

  size_t block = BLOCK_FROM_PTR(ptr);
  if (ATB_GET_KIND(block) == AT_TAIL) {
    return 0;
  }
  size_t n = 0;
  do {
    ++n;
  } while (ATB_GET_KIND(block + n) == AT_TAIL);
  return n;
}

void dump_value(FILE *out, mp_const_obj_t value);

void mark(void const *const ptr) {
  if (!VERIFY_PTR(ptr)) return;
  size_t block = BLOCK_FROM_PTR(ptr);
  if (ATB_GET_KIND(block) == AT_HEAD) {
    ATB_HEAD_TO_MARK(block);
  }
}

bool is_short(mp_const_obj_t value) {
  return value == NULL || value == MP_OBJ_NULL || mp_obj_is_qstr(value) ||
         mp_obj_is_small_int(value) || !VERIFY_PTR(value);
}

static void print_type(FILE *out, const char *typename, const char *shortval,
                       const void *ptr, bool end) {
  static char unescaped[1000];
  size_t size = 0;
  if (!is_short(ptr)) {
    size = find_allocated_size(ptr);
  }
  fprintf(out, "{\"type\": \"%s\", \"alloc\": %ld, \"ptr\": \"%p\"", typename,
          size, ptr);
  if (shortval) {
    assert(strlen(shortval) < 1000);
    char *c = unescaped;
    while (*shortval) {
      if (*shortval == '\\' || *shortval == '"') *c++ = '\\';
      *c++ = *shortval++;
    }
    *c = 0;
    fprintf(out, ", \"shortval\": \"%s\"", unescaped);
  } else {
    fprintf(out, ", \"shortval\": null");
  }
  if (end) fprintf(out, "}");
}

static void print_repr(FILE *out, const char *strbuf, size_t buflen) {
  fprintf(out, "\"");
  for (size_t i = 0; i < buflen; ++i) {
    if (strbuf[i] == '\\')
      fprintf(out, "\\\\");
    else if (strbuf[i] == '"')
      fprintf(out, "\\\"");
    else if (strbuf[i] >= 0x20 && strbuf[i] <= 0x7e)
      fprintf(out, "%c", strbuf[i]);
    else
      fprintf(out, "\\\\x%02x", (unsigned char)strbuf[i]);
  }
  fprintf(out, "\"");
}

void dump_short(FILE *out, mp_const_obj_t value) {
  fflush(out);
  if (value == NULL || value == MP_OBJ_NULL) {
    fprintf(out, "null");

  } else if (mp_obj_is_qstr(value)) {
    mp_int_t q = MP_OBJ_QSTR_VALUE(value);
    print_type(out, "qstr", qstr_str(q), NULL, true);

  } else if (mp_obj_is_small_int(value)) {
    static char num_buf[100];
    snprintf(num_buf, 100, "%ld", MP_OBJ_SMALL_INT_VALUE(value));
    print_type(out, "smallint", num_buf, NULL, true);

  } else if (!VERIFY_PTR(value)) {
    print_type(out, "romdata", NULL, value, true);
  }
}

void dump_short_or_ptr(FILE *out, mp_const_obj_t value) {
  if (is_short(value))
    dump_short(out, value);
  else
    fprintf(out, "\"%p\"", value);
}

void dump_map_as_children(FILE *out, const mp_map_t *map) {
  fprintf(out, ", \"children\": [");
  bool first = true;
  for (size_t i = 0; i < map->alloc; ++i) {
    if (!mp_map_slot_is_filled(map, i)) continue;
    if (!first) fprintf(out, ",\n");
    first = false;
    fprintf(out, "{\"key\": ");
    dump_short_or_ptr(out, map->table[i].key);
    fprintf(out, ",\n\"value\": ");
    dump_short_or_ptr(out, map->table[i].value);
    fprintf(out, "}");
  }
  fprintf(out, "]");
}

void dump_map_as_values(FILE *out, const void *const owner,
                        const mp_map_t *map) {
  print_type(out, "mapitems", NULL, map->table, false);
  fprintf(out, ",\n\"owner\": \"%p\"", owner);
  fprintf(out, "},\n");

  for (size_t i = 0; i < map->alloc; ++i) {
    if (!mp_map_slot_is_filled(map, i)) continue;
    dump_value(out, map->table[i].key);
    dump_value(out, map->table[i].value);
  }
}

void dump_dict_inner(FILE *out, const mp_obj_dict_t *dict) {
  print_type(out, "dict", NULL, dict, false);
  dump_map_as_children(out, &dict->map);
  fprintf(out, "},\n");
  dump_map_as_values(out, dict, &dict->map);
}

void dump_function(FILE *out, const mp_obj_fun_bc_t *func) {
  print_type(out, "function", NULL, func, false);
  fprintf(out, ",\n\"globals\": \"%p\"", func->globals);
  fprintf(out, ",\n\"code_alloc\": %ld", find_allocated_size(func->bytecode));
  fprintf(out, ",\n\"code_ptr\": \"%p\"", func->bytecode);
  fprintf(out, ",\n\"const_table_alloc\": %ld",
          find_allocated_size(func->const_table));
  fprintf(out, ",\n\"const_table_ptr\": \"%p\"", func->const_table);
  mark(func->bytecode);
  mark(func->const_table);
  fprintf(out, "},\n");

  dump_value(out, func->globals);
}

typedef struct _mp_obj_bound_meth_t {
  mp_obj_base_t base;
  mp_obj_t meth;
  mp_obj_t self;
} mp_obj_bound_meth_t;

typedef struct _mp_obj_closure_t {
  mp_obj_base_t base;
  mp_obj_t fun;
  size_t n_closed;
  mp_obj_t closed[];
} mp_obj_closure_t;

extern const mp_obj_type_t mp_type_bound_meth;
extern const mp_obj_type_t mp_type_closure;
extern const mp_obj_type_t mp_type_cell;
extern const mp_obj_type_t mod_trezorio_WebUSB_type;
extern const mp_obj_type_t mod_trezorio_USB_type;
extern const mp_obj_type_t mod_trezorio_VCP_type;
extern const mp_obj_type_t mod_trezorio_HID_type;
extern const mp_obj_type_t mod_trezorui_Display_type;

typedef struct _mp_obj_WebUSB_t {
  mp_obj_base_t base;
  usb_webusb_info_t info;
} mp_obj_WebUSB_t;

typedef struct _mp_obj_VCP_t {
  mp_obj_base_t base;
  usb_vcp_info_t info;
} mp_obj_VCP_t;

typedef struct _mp_obj_HID_t {
  mp_obj_base_t base;
  usb_hid_info_t info;
} mp_obj_HID_t;

typedef struct _mp_obj_protomsg_t {
  mp_obj_base_t base;
  mp_map_t map;
} mp_obj_protomsg_t;

typedef struct _mp_obj_uilayout_t {
  mp_obj_base_t base;
  ssize_t _refcell_borrow_flag;
  void *inner;
} mp_obj_uilayout_t;

void dump_bound_method(FILE *out, const mp_obj_bound_meth_t *meth) {
  print_type(out, "method", NULL, meth, false);

  fprintf(out, ",\n\"self\": \"%p\"", meth->self);
  fprintf(out, ",\n\"body\": \"%p\"", meth->meth);
  fprintf(out, "},");

  dump_value(out, meth->self);
  dump_value(out, meth->meth);
}

void dump_static_method(FILE *out, const mp_obj_static_class_method_t *meth) {
  print_type(out, "staticmethod", NULL, meth, false);
  fprintf(out, ",\n\"body\": \"%p\"", meth->fun);
  fprintf(out, "},");
  dump_value(out, meth->fun);
}

void dump_closure(FILE *out, const mp_obj_closure_t *closure) {
  size_t size = find_allocated_size(closure);
  for (size_t i = 0; i < closure->n_closed; ++i) {
    // XXX this is unimportant to track properly, hopefully
    size += find_allocated_size(closure->closed[i]);
    assert(mp_obj_is_type(closure->closed[i], &mp_type_cell));
  }
  print_type(out, "closure", NULL, closure, false);

  fprintf(out, ",\n\"function\": \"%p\"", closure->fun);
  fprintf(out, ",\n\"closed\": [\n");
  bool first = true;
  for (size_t i = 0; i < closure->n_closed; ++i) {
    if (!first) fprintf(out, ",\n");
    first = false;
    dump_short_or_ptr(out, mp_obj_cell_get(closure->closed[i]));
  }
  fprintf(out, "]},");

  dump_value(out, closure->fun);
  for (size_t i = 0; i < closure->n_closed; ++i) {
    dump_value(out, mp_obj_cell_get(closure->closed[i]));
  }
}

typedef struct _mp_obj_gen_instance_t {
  mp_obj_base_t base;
  // mp_const_none: Not-running, no exception.
  // MP_OBJ_NULL: Running, no exception.
  // other: Not running, pending exception.
  mp_obj_t pend_exc;
  mp_code_state_t code_state;
} mp_obj_gen_instance_t;

void dump_generator(FILE *out, const mp_obj_gen_instance_t *gen) {
  print_type(out, "generator", NULL, gen, false);

  fprintf(out, ",\n\"pending_exception\": \"%p\"", gen->pend_exc);
  fprintf(out, ",\n\"function\": \"%p\"", gen->code_state.fun_bc);
  fprintf(out, ",\n\"old_globals\": \"%p\"", gen->code_state.old_globals);
  fprintf(out, ",\n\"state\": [\n");
  bool first = true;
  for (size_t i = 0; i < gen->code_state.n_state; ++i) {
    if (!first) fprintf(out, ",\n");
    first = false;
    dump_short_or_ptr(out, gen->code_state.state[i]);
  }

  fprintf(out, "]},\n");
  dump_value(out, gen->pend_exc);
  dump_value(out, gen->code_state.fun_bc);
  dump_value(out, gen->code_state.old_globals);
  for (size_t i = 0; i < gen->code_state.n_state; ++i) {
    dump_value(out, gen->code_state.state[i]);
  }
}

void dump_instance(FILE *out, const mp_obj_instance_t *obj) {
  print_type(out, "instance", NULL, obj, false);
  fprintf(out, ",\n\"base\": \"%p\"", obj->base.type);
  dump_map_as_children(out, &obj->members);
  fprintf(out, "},\n");

  dump_value(out, obj->base.type);
  dump_map_as_values(out, obj, &obj->members);
}

void dump_type(FILE *out, const mp_obj_type_t *type) {
  print_type(out, "type", qstr_str(type->name), type, false);
  fprintf(out, ",\n\"locals\": \"%p\"", type->locals_dict);
  fprintf(out, ",\n\"parent\": \"%p\"},\n", type->parent);

  dump_value(out, type->parent);
  dump_value(out, type->locals_dict);
}

void dump_list(FILE *out, const mp_obj_list_t *list) {
  print_type(out, "list", NULL, list, false);
  fprintf(out, ",\n\"items\": [\n");
  bool first = true;
  for (size_t i = 0; i < list->len; ++i) {
    if (!first) fprintf(out, ",\n");
    first = false;
    dump_short_or_ptr(out, list->items[i]);
  }
  fprintf(out, "]},\n");

  print_type(out, "listitems", NULL, list->items, false);
  fprintf(out, ",\n\"owner\": \"%p\"},\n", list);
  for (size_t i = 0; i < list->len; ++i) {
    dump_value(out, list->items[i]);
  }
}

void dump_tuple(FILE *out, const mp_obj_tuple_t *tuple) {
  print_type(out, "tuple", NULL, tuple, false);
  fprintf(out, ",\n\"items\": [\n");
  bool first = true;
  for (size_t i = 0; i < tuple->len; ++i) {
    if (!first) fprintf(out, ",\n");
    first = false;
    dump_short_or_ptr(out, tuple->items[i]);
  }
  fprintf(out, "]},\n");

  for (size_t i = 0; i < tuple->len; ++i) {
    dump_value(out, tuple->items[i]);
  }
}

typedef struct _mp_obj_set_t {
  mp_obj_base_t base;
  mp_set_t set;
} mp_obj_set_t;

bool is_set_or_frozenset(mp_const_obj_t o);

void dump_set(FILE *out, const mp_obj_set_t *set) {
  print_type(out, "set", NULL, set, false);
  fprintf(out, ",\n\"items\": [\n");
  bool first = true;
  for (size_t i = 0; i < set->set.alloc; ++i) {
    if (!mp_set_slot_is_filled(&set->set, i)) continue;
    if (!first) fprintf(out, ",\n");
    first = false;
    dump_short_or_ptr(out, set->set.table[i]);
  }
  fprintf(out, "]},\n");

  print_type(out, "setitems", NULL, set->set.table, false);
  fprintf(out, ",\n\"owner\": \"%p\"},\n", set);

  for (size_t i = 0; i < set->set.alloc; ++i) {
    if (!mp_set_slot_is_filled(&set->set, i)) continue;
    dump_value(out, set->set.table[i]);
  }
}

void dump_trezor_hid(FILE *out, const mp_obj_HID_t *hid) {
  print_type(out, "trezor-hid", NULL, hid, false);
  fprintf(out, ",\n\"rx_buffer\": \"%p\"},\n", hid->info.rx_buffer);
  print_type(out, "rawbuffer", NULL, hid->info.rx_buffer, true);
  fprintf(out, ",\n");
}

void dump_trezor_webusb(FILE *out, const mp_obj_WebUSB_t *webusb) {
  print_type(out, "trezor-webusb", NULL, webusb, false);
  fprintf(out, ",\n\"rx_buffer\": \"%p\"},\n", webusb->info.rx_buffer);
  print_type(out, "rawbuffer", NULL, webusb->info.rx_buffer, true);
  fprintf(out, ",\n");
}

void dump_trezor_vcp(FILE *out, const mp_obj_VCP_t *vcp) {
  print_type(out, "trezor-vcp", NULL, vcp, false);
  fprintf(out, ",\n\"tx_packet\": \"%p\"", vcp->info.tx_packet);
  fprintf(out, ",\n\"tx_buffer\": \"%p\"", vcp->info.tx_buffer);
  fprintf(out, ",\n\"rx_packet\": \"%p\"", vcp->info.rx_packet);
  fprintf(out, ",\n\"rx_buffer\": \"%p\"},\n", vcp->info.rx_buffer);
  print_type(out, "rawbuffer", NULL, vcp->info.tx_packet, true);
  fprintf(out, ",\n");
  print_type(out, "rawbuffer", NULL, vcp->info.tx_buffer, true);
  fprintf(out, ",\n");
  print_type(out, "rawbuffer", NULL, vcp->info.rx_packet, true);
  fprintf(out, ",\n");
  print_type(out, "rawbuffer", NULL, vcp->info.rx_buffer, true);
  fprintf(out, ",\n");
}

void dump_protomsg(FILE *out, const mp_obj_protomsg_t *value) {
  mp_obj_t name[2] = {MP_OBJ_NULL, MP_OBJ_NULL};
  mp_obj_type_t *type = protobuf_debug_msg_type();
  type->attr((mp_obj_t)value, MP_QSTR_MESSAGE_NAME, name);

  print_type(out, "protomsg", NULL, value, false);
  fprintf(out, ",\n\"message_name\": ");
  dump_short(out, name[0]);
  dump_map_as_children(out, &value->map);
  fprintf(out, "},\n");
}

void dump_protodef(FILE *out, const mp_obj_t *value) {
  mp_obj_t name[2] = {MP_OBJ_NULL, MP_OBJ_NULL};
  mp_obj_type_t *type = protobuf_debug_msg_def_type();
  type->attr((mp_obj_t)value, MP_QSTR_MESSAGE_NAME, name);

  print_type(out, "protodef", NULL, value, false);
  fprintf(out, ",\n\"message_name\": ");
  dump_short(out, name[0]);
  fprintf(out, "},\n");
}

void dump_uilayout(FILE *out, const mp_obj_uilayout_t *value) {
  print_type(out, "uilayout", NULL, value, false);
  fprintf(out, ",\n\"inner\": \"%p\"},\n", value->inner);
  print_type(out, "uilayoutinner", NULL, value->inner, true);
  fprintf(out, ",\n");
}

void dump_value_opt(FILE *out, mp_const_obj_t value, bool eval_short) {
  if (!eval_short && is_short(value)) return;

  if (!eval_short || VERIFY_PTR(value)) {
    size_t block = BLOCK_FROM_PTR(value);
    switch (ATB_GET_KIND(block)) {
      case AT_HEAD:
        // all is ok
        ATB_HEAD_TO_MARK(block);
        break;
      case AT_TAIL:
        printf("===== pointer to tail???\n");
        break;
      case AT_MARK:
        // print_type(out, "already_dumped", 0, NULL, value);
        return;
    }
  }

  if (mp_obj_is_str_or_bytes(value)) {
    const mp_obj_str_t *strvalue = (mp_obj_str_t *)value;
    print_type(out, "anystr", NULL, value, false);
    fprintf(out, ", \"val\": ");
    print_repr(out, (const char *)strvalue->data, strvalue->len);
    fprintf(out, ", \"data\": \"%p\"", strvalue->data);
    fprintf(out, "},\n");
    print_type(out, "strdata", NULL, strvalue->data, true);
    fprintf(out, ",\n");
  }

  else if (mp_obj_is_type(value, &mp_type_bytearray)) {
    const mp_obj_array_t *array = (mp_obj_array_t *)value;
    print_type(out, "array", NULL, array, true);
    fprintf(out, ",\n");
    print_type(out, "arrayitems", NULL, array->items, false);
    fprintf(out, ", \"owner\": \"%p\"}", array);
    fprintf(out, ",\n");
  }

  else if (mp_obj_is_type(value, &mp_type_dict)) {
    dump_dict_inner(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_module)) {
    print_type(out, "module", NULL, value, false);
    mp_obj_module_t *module = MP_OBJ_TO_PTR(value);
    fprintf(out, ", \"globals\": \"%p\"", module->globals);
    fprintf(out, "},\n");
    dump_value(out, module->globals);
  }

  else if (mp_obj_is_type(value, &mp_type_fun_bc) ||
           mp_obj_is_type(value, &mp_type_gen_wrap)) {
    dump_function(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_bound_meth)) {
    dump_bound_method(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_closure)) {
    dump_closure(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_staticmethod) ||
           mp_obj_is_type(value, &mp_type_classmethod)) {
    dump_static_method(out, value);
  }

  else if (mp_obj_is_instance_type(mp_obj_get_type(value))) {
    dump_instance(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_object)) {
    print_type(out, "object", NULL, value, true);
    fprintf(out, ",\n");
  }

  else if (mp_obj_is_type(value, &mp_type_type)) {
    dump_type(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_list)) {
    dump_list(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_tuple)) {
    dump_tuple(out, value);
  }

  else if (is_set_or_frozenset(value)) {
    dump_set(out, value);
  }

  else if (mp_obj_is_type(value, &mp_type_gen_instance)) {
    dump_generator(out, value);
  }

  else if (mp_obj_is_type(value, &mod_trezorio_WebUSB_type)) {
    dump_trezor_webusb(out, value);
  }

  else if (mp_obj_is_type(value, &mod_trezorio_VCP_type)) {
    dump_trezor_vcp(out, value);
  }

  else if (mp_obj_is_type(value, &mod_trezorio_HID_type)) {
    dump_trezor_hid(out, value);
  }

  else if (mp_obj_is_type(value, &mod_trezorio_USB_type) ||
           mp_obj_is_type(value, &mod_trezorui_Display_type)) {
    print_type(out, "trezor", NULL, value, true);
    fprintf(out, ",\n");
  }

  else if (mp_obj_is_type(value, protobuf_debug_msg_type())) {
    dump_protomsg(out, value);
  }

  else if (mp_obj_is_type(value, protobuf_debug_msg_def_type())) {
    dump_protodef(out, value);
  }

  else if (mp_obj_is_type(value, ui_debug_layout_type())) {
    dump_uilayout(out, value);
  }

  else {
    print_type(out, "unknown", NULL, value, true);
    fprintf(out, ",\n");
  }

  fflush(out);
}

void dump_value(FILE *out, mp_const_obj_t value) {
  dump_value_opt(out, value, false);
}

void dump_qstr_pool(FILE *out, qstr_pool_t *pool) {
  print_type(out, "qstrpool", NULL, pool, false);
  fprintf(out, ", \"qstrs\": [\n");
  for (const byte **q = pool->qstrs, **q_top = pool->qstrs + pool->len;
       q < q_top; q++) {
    if (q < (q_top - 1))
      fprintf(out, "\"%s\",\n", Q_GET_DATA(*q));
    else
      fprintf(out, "\"%s\"]\n", Q_GET_DATA(*q));
  }
  fprintf(out, "},\n");
  for (const byte **q = pool->qstrs, **q_top = pool->qstrs + pool->len;
       q < q_top; q++) {
    print_type(out, "qstrdata", NULL, *q, false);
    fprintf(out, ", \"pool\": \"%p\"},\n", pool);
  }
}

void dump_qstrdata(FILE *out) {
  qstr_pool_t *pool = MP_STATE_VM(last_pool);
  while (pool != NULL) {
    for (const byte **q = pool->qstrs, **q_top = pool->qstrs + pool->len;
         q < q_top; q++) {
      if ((void *)*q > (void *)mp_state_ctx.mem.gc_pool_start) {
        print_type(out, "qstrdata", NULL, q, false);
        fprintf(out, ", \"pool\": \"%p\"},\n", pool);
      }
    }
    pool = pool->prev;
  }
}

/// def meminfo(filename: str) -> None:
///     """Dumps map of micropython GC arena to a file.
///     The JSON file can be decoded by analyze.py
///     Only available in the emulator.
///      """
STATIC mp_obj_t mod_trezorutils_meminfo(mp_obj_t filename) {
  size_t fn_len;
  FILE *out = fopen(mp_obj_str_get_data(filename, &fn_len), "w");
  fprintf(out, "[");

  // void **ptrs = (void **)(void *)&mp_state_ctx;
  // size_t root_start = offsetof(mp_state_ctx_t, thread.dict_locals);
  // size_t root_end = offsetof(mp_state_ctx_t, vm.qstr_last_chunk);

  // for (size_t i = root_start; i < root_end; i++) {
  //     void *ptr = ptrs[i];
  //     if (i == 55) continue; // mp_loaded_modules_dict
  //     if (i == 62) continue; // dict_main
  //     if (i == 66) continue; // mp_sys_path_obj
  //     if (i == 70) continue; // mp_sys_argv_obj
  //     if (i == 123) continue; // qstr_last_chunk
  //     if (VERIFY_PTR(ptr)) {
  //         size_t block = BLOCK_FROM_PTR(ptr);
  //         if (ATB_GET_KIND(block) == AT_HEAD) {
  //           fprintf(out, "\"root_ofs: %ld\",\n", i);
  //           dump_value(out, ptr);
  //             // // An unmarked head: mark it, and mark all its children
  //             // TRACE_MARK(block, ptr);
  //             // ATB_HEAD_TO_MARK(block);
  //             // gc_mark_subtree(block);
  //         }
  //     }
  // }

  fprintf(out, "\"dict_locals\",\n");
  dump_value(out, MP_STATE_THREAD(dict_locals));

  fprintf(out, "\"mp_loaded_modules_dict\",\n");
  dump_value_opt(out, &MP_STATE_VM(mp_loaded_modules_dict), true);

  fprintf(out, "\"dict_main\",\n");
  dump_value_opt(out, &MP_STATE_VM(dict_main), true);

  fprintf(out, "\"mp_sys_path_obj\",\n");
  dump_value_opt(out, &MP_STATE_VM(mp_sys_path_obj), true);

  fprintf(out, "\"mp_sys_argv_obj\",\n");
  dump_value_opt(out, &MP_STATE_VM(mp_sys_argv_obj), true);

  fprintf(out, "\"ui_wait_callback\",\n");
  dump_value(out, MP_STATE_VM(trezorconfig_ui_wait_callback));

  fprintf(out, "\"qstr_pools\",\n");
  qstr_pool_t *pool = MP_STATE_VM(last_pool);
  while (VERIFY_PTR((void *)pool)) {
    dump_qstr_pool(out, pool);
    pool = pool->prev;
  }

  fprintf(out, "null]\n");
  fclose(out);
  for (size_t block = 0;
       block < MP_STATE_MEM(gc_alloc_table_byte_len) * BLOCKS_PER_ATB;
       block++) {
    if (ATB_GET_KIND(block) == AT_MARK) {
      ATB_MARK_TO_HEAD(block);
    }
  }

  gc_dump_alloc_table();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_meminfo_obj,
                                 mod_trezorutils_meminfo);

#define MEMINFO_DICT_ENTRIES \
  {MP_ROM_QSTR(MP_QSTR_meminfo), MP_ROM_PTR(&mod_trezorutils_meminfo_obj)},

#endif
