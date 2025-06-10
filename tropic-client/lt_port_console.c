#include "libtropic_common.h"
#include "libtropic_port.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

lt_ret_t lt_port_init(lt_l2_state_t *s2) {
    return LT_OK;
}

lt_ret_t lt_port_deinit(lt_l2_state_t *s2) {
    return LT_OK;
}

lt_ret_t lt_port_spi_csn_low(lt_l2_state_t *s2) {
    return LT_OK;
}

lt_ret_t lt_port_spi_csn_high(lt_l2_state_t *s2) {
    return LT_OK;
}

lt_ret_t lt_port_spi_transfer(lt_l2_state_t *s2, uint8_t offset, uint16_t tx_len, uint32_t timeout) {
    return LT_OK;
}
lt_ret_t lt_port_delay(lt_l2_state_t *s2, uint32_t ms) {
    return LT_OK;
}

lt_ret_t lt_port_random_bytes(uint32_t *buff, uint16_t len) {
  for (int i = 0; i < len; i++) {
    buff[i] = 0xabcdabcd;
  }

  return LT_OK;
}
