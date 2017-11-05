
#include "lib/utils/interrupt_char.h"

static inline mp_uint_t mp_hal_ticks_cpu(void) {
    return 0;
}

void mp_hal_set_vcp_iface(int iface_num);
