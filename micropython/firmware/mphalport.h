#include STM32_HAL_H

#include "lib/utils/interrupt_char.h"

#define MP_HAL_UNIQUE_ID_ADDRESS (0x1fff7a10)

#define MP_PLAT_PRINT_STRN(str, len) mp_hal_stdout_tx_strn_cooked(str, len)

static inline mp_uint_t mp_hal_ticks_cpu(void) {
    return DWT->CYCCNT;
}
