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

#ifndef TREZORHAL_I2C_NEW_H
#define TREZORHAL_I2C_NEW_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// I2C bus abstraction
typedef struct i2c_bus i2c_bus_t;
// I2C packet (series of I2C operations)
typedef struct i2c_packet i2c_packet_t;
// I2C operation (single transfer)
typedef struct i2c_op i2c_op_t;

// Completion callback
typedef void (*i2c_callback_t)(void* context, i2c_packet_t* packet);

// I2C packet status
typedef enum {
  I2C_STATUS_OK = 0,       // Packet completed successfully
  I2C_STATUS_PENDING = 1,  // Packet is pending
  I2C_STATUS_INVARG = 2,   // Invalid packet/op parameters
  I2C_STATUS_BUSY = 3,     // Bus is busy
  I2C_STATUS_TIMEOUT = 4,  // Timeout occurred
  I2C_STATUS_NACK = 5,     // Device did not acknowledge
  I2C_STATUS_ERROR = 6,    // General error

} i2c_status_t;

struct i2c_packet {
  // Next packet in the driver queue
  i2c_packet_t* next;
  // I2C device address (7-bit address)
  uint8_t address;
  // I2C_STATUS_xxx
  i2c_status_t status;
  // Number of operations
  uint8_t op_count;
  // Pointer to array of operations
  i2c_op_t* ops;
  // Completion callback function
  i2c_callback_t callback;
  // Callback context (user provided data)
  void* context;
};

// I2C operation flags
#define I2C_FLAG_START 0x0001     // Generate start condition
#define I2C_FLAG_STOP 0x0002      // Generate stop condition
#define I2C_FLAG_WRITE 0x0004     // Write operation
#define I2C_FLAG_READ 0x0008      // Read operation
#define I2C_FLAG_EMBEDDED 0x0010  // Embedded data (no pointer)

// I2C operation flags constraints:
// 1) I2C_FLAG_WRITE | I2C_FLAG_READ is not allowed
// 2) if I2C_FLAG_EMBEDED is set, size must be <= 4

struct i2c_op {
  // I2C_FLAG_xxx
  uint16_t flags;
  // Number of bytes to transfer
  uint16_t size;
  // Data to read or write
  union {
    // Pointer to data (I2C_FLAG_EMBEDDED is not set)
    void* ptr;
    // Embedded data (I2C_FLAG_EMBEDDED is set)
    uint8_t data[4];
  };
};

// Gets I2C bus handle by index
//
// Returns NULL if bus is not available.
// If the bus was not acquired before, it will be initialized.
i2c_bus_t* i2c_bus_acquire(uint8_t bus_index);

// Releases I2C bus handle
void i2c_bus_release(i2c_bus_t* bus);

// Submits I2C packet to the bus
i2c_status_t i2c_packet_submit(i2c_bus_t* bus, i2c_packet_t* packet);

// Returns I2C packet status
//
// If the packet is not completed yet, it returns I2C_STATUS_PENDING.
i2c_status_t i2c_packet_status(i2c_packet_t* packet);

// Waits until I2C packet is completed and returns its status
i2c_status_t i2c_packet_wait(i2c_packet_t* packet);

/*
void example() {

    static uint8_t data_in;
    static uint8_t data_out;

    static i2c_op_t ops[2] = {
        {
            .flags = I2C_FLAG_START | I2C_FLAG_WRITE,
            .size = 1,
            .ptr = &data_in;
        },
        {
            .flags = I2C_FLAG_STOP | I2C_FLAG_READ | I2C_FLAG_EMBED,
            .size = 1,
            .data = 0x10;
        },
    };

    static i2c_packet_t pkt = {
        .callback = NULL,
        .context = NULL,
        .op_count = ARRAY_SIZE(ops),
        .ops = ops,
        },
    };

    status = i2c_packet_submit(bus, &pkt);

    status = i2c_packet_wait(&pkt);
}
*/

#endif  // TREZORHAL_I2C_NEW_H
