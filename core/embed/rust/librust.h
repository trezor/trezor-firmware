#include "librust_qstr.h"

mp_obj_t protobuf_type_for_name(mp_obj_t name);
mp_obj_t protobuf_type_for_wire(mp_obj_t wire_id);
mp_obj_t protobuf_decode(mp_obj_t buf, mp_obj_t def,
                         mp_obj_t enable_experimental);
mp_obj_t protobuf_len(mp_obj_t obj);
mp_obj_t protobuf_encode(mp_obj_t buf, mp_obj_t obj);
