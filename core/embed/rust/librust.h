#include "librust_qstr.h"

mp_obj_t protobuf_type_for_name(mp_obj_t name);
mp_obj_t protobuf_type_for_wire(mp_obj_t wire_id);
mp_obj_t protobuf_decode(mp_obj_t buf, mp_obj_t def,
                         mp_obj_t enable_experimental);
mp_obj_t protobuf_len(mp_obj_t obj);
mp_obj_t protobuf_encode(mp_obj_t buf, mp_obj_t obj);

#ifdef TREZOR_EMULATOR
mp_obj_t protobuf_debug_msg_type();
mp_obj_t protobuf_debug_msg_def_type();
#endif

mp_obj_t ui_layout_new_example(mp_obj_t);
mp_obj_t ui_layout_new_confirm_action(size_t n_args, const mp_obj_t *args,
                                      mp_map_t *kwargs);

#ifdef TREZOR_EMULATOR
mp_obj_t ui_debug_layout_type();
#endif
