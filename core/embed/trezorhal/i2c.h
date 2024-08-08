/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef TREZORHAL_I2C_H
#define TREZORHAL_I2C_H

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

#endif  // TREZORHAL_I2C_H
