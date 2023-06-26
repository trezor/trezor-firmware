#include "py/obj.h"

#include "librust_qstr.h"

#ifdef TREZOR_EMULATOR
mp_obj_t protobuf_debug_msg_type();
mp_obj_t protobuf_debug_msg_def_type();
#endif

extern mp_obj_module_t mp_module_trezorproto;
extern mp_obj_module_t mp_module_trezorui2;

#ifdef TREZOR_EMULATOR
mp_obj_t ui_debug_layout_type();
#endif
