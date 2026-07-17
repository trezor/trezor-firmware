#include "py/obj.h"
#include "py/objlist.h"

// Static wrappers

void mp_obj_list_get__extern(mp_obj_t self_in, size_t *len, mp_obj_t **items) {
  mp_obj_list_get(self_in, len, items);
}
void mp_obj_list_set_len__extern(mp_obj_t self_in, size_t len) {
  mp_obj_list_set_len(self_in, len);
}
