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

// TODO: BITCOIN_ONLY conditional
mp_obj_t zcash_diag(mp_obj_t ins, mp_obj_t data);
mp_obj_t zcash_get_orchard_fvk(mp_obj_t sk);
mp_obj_t zcash_get_orchard_ivk(mp_obj_t sk);
mp_obj_t zcash_get_orchard_address(mp_obj_t sk, mp_obj_t diversifier_index);
mp_obj_t zcash_f4jumble(mp_obj_t message);
mp_obj_t zcash_f4jumble_inv(mp_obj_t message);