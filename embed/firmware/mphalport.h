#include STM32_HAL_H

#include "lib/utils/interrupt_char.h"

static inline mp_uint_t mp_hal_ticks_cpu(void) {
    return DWT->CYCCNT;
}

void mp_hal_set_vcp_iface(int iface_num);
