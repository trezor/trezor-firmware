
#include STM32_HAL_H

void i2c_init(void);
void i2c_cycle(void);
HAL_StatusTypeDef i2c_transmit(uint8_t addr, uint8_t *data, uint16_t len,
                               uint32_t timeout);
HAL_StatusTypeDef i2c_receive(uint8_t addr, uint8_t *data, uint16_t len,
                              uint32_t timeout);
