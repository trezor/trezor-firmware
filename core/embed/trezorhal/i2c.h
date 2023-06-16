
#include STM32_HAL_H

void i2c_init(void);
void i2c_cycle(uint16_t idx);
HAL_StatusTypeDef i2c_transmit(uint16_t idx, uint8_t addr, uint8_t *data,
                               uint16_t len, uint32_t timeout);
HAL_StatusTypeDef i2c_receive(uint16_t idx, uint8_t addr, uint8_t *data,
                              uint16_t len, uint32_t timeout);
HAL_StatusTypeDef i2c_mem_write(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                                uint16_t mem_addr_size, uint8_t *data,
                                uint16_t len, uint32_t timeout);
HAL_StatusTypeDef i2c_mem_read(uint16_t idx, uint8_t addr, uint16_t mem_addr,
                               uint16_t mem_addr_size, uint8_t *data,
                               uint16_t len, uint32_t timeout);
