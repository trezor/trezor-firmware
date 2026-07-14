#include "py/obj.h"

#include "librust_qstr.h"

#if !PYOPT
mp_obj_t protobuf_debug_msg_type();
mp_obj_t protobuf_debug_msg_def_type();
#endif

extern const mp_obj_module_t mp_module_trezorproto;
extern const mp_obj_module_t mp_module_trezorui_api;
extern const mp_obj_module_t mp_module_trezortranslate;
extern const mp_obj_module_t mp_module_trezorble;
extern const mp_obj_module_t mp_module_trezorthp;

#ifdef USE_DBG_CONSOLE
extern const mp_obj_module_t mp_module_trezorlog;
#endif

#if !PYOPT
mp_obj_t ui_debug_layout_type();

#ifdef TREZOR_EMULATOR
extern const mp_obj_module_t mp_module_coveragedata;
#endif

#endif
