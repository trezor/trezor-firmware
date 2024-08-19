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

#include "i2c_new.h"

struct i2c_bus {
  int dummy;
};

i2c_bus_t* i2c_bus_acquire(uint8_t bus_index) { return NULL; }

void i2c_bus_release(i2c_bus_t* bus) {}

i2c_status_t i2c_packet_submit(i2c_bus_t* bus, i2c_packet_t* packet) {
  return I2C_STATUS_ERROR;
}

i2c_status_t i2c_packet_status(i2c_packet_t* packet) {
  return I2C_STATUS_ERROR;
}

i2c_status_t i2c_packet_wait(i2c_packet_t* packet) { return I2C_STATUS_ERROR; }
