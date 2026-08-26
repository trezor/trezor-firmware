#include "py/obj.h"

#include "librust_qstr.h"

#if !PYOPT
mp_obj_t protobuf_debug_msg_type();
mp_obj_t protobuf_debug_msg_def_type();
#endif

#if !PYOPT
mp_obj_t ui_debug_layout_type();
#endif
