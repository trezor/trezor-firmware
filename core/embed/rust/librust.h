#include "librust_qstr.h"

mp_obj_t ui_render_rich_text(const mp_map_t *kw);
mp_obj_t ui_layout_new_example(void);

mp_obj_t protobuf_type(mp_obj_t name);
mp_obj_t protobuf_decode(mp_obj_t buf, mp_obj_t def);
mp_obj_t protobuf_encode(mp_obj_t buf, mp_obj_t def, mp_obj_t obj);
