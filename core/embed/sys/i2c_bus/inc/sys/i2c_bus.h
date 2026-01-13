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

#ifndef TREZORHAL_I2C_BUS_H
#define TREZORHAL_I2C_BUS_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

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
  I2C_STATUS_ABORTED = 7,  // Packet was aborted

} i2c_status_t;

struct i2c_packet {
  // Next packet in the driver queue
  i2c_packet_t* next;
  // I2C device address (7-bit address)
  uint8_t address;
  // Extra timeout (in milliseconds) added to the default timeout
  // to finish each operation
  uint16_t timeout;
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
#define I2C_FLAG_START 0x0001  // Generate START condition before the operation
#define I2C_FLAG_STOP 0x0002   // Generate STOP after the operation
#define I2C_FLAG_TX 0x0004     // Transmit data
#define I2C_FLAG_RX 0x0008     // Receive data
#define I2C_FLAG_EMBED 0x0010  // Embedded data (no reference)

// I2C operation flags constraints:
// 1) I2C_FLAG_TX | I2C_FLAG_RX is not allowed
// 2) if I2C_FLAG_EMBED is set, size must be <= 4

struct i2c_op {
  // I2C_FLAG_xxx
  uint16_t flags;
  // Number of bytes to transfer
  uint16_t size;
  // Data to read or write
  union {
    // Pointer to data (I2C_FLAG_EMBED is not set)
    void* ptr;
    // Embedded data (I2C_FLAG_EMBED is set)
    uint8_t data[4];
  };
};

// Acquires I2C bus reference by index (0..2 according to the model)
//
// Returns NULL if bus is not available or can't be initialized.
//
// If the bus was not acquired before, it will be initialized.
i2c_bus_t* i2c_bus_open(uint8_t bus_index);

// Closes I2C bus handle
//
// After releasing the last bus reference, the bus will be deinitialized.
void i2c_bus_close(i2c_bus_t* bus);

// Submits I2C packet to the bus
//
// After submitting the packet, the packet status will be set to
// I2C_STATUS_PENDING until the packet is completed.
//
// The caller must not modify the packet (or data pointed by the packet)
// until the packet is completed (callback is called or status
// is not I2C_STATUS_PENDING).
//
// Returns:
//   I2C_STATUS_OK  -- packet was successfully submitted
i2c_status_t i2c_bus_submit(i2c_bus_t* bus, i2c_packet_t* packet);

// Aborts pending or queue packet
//
// Immediately after calling this function, the packet status will be
// set to I2C_STATUS_ABORTED and I2C driver will not access the packet anymore.
//
// If the packet is already completed, it does nothing.
// If the packet is queued it will be removed from the queue.
// If the packet is pending, it will be aborted.
// In any case completion callback will not be called.
void i2c_bus_abort(i2c_bus_t* bus, i2c_packet_t* packet);

// Returns I2C packet status
//
// If the packet is not completed yet, it returns I2C_STATUS_PENDING.
i2c_status_t i2c_packet_status(const i2c_packet_t* packet);

// Waits until I2C packet is completed and returns its final status
i2c_status_t i2c_packet_wait(const i2c_packet_t* packet);

// Helper function to submit and wait for the packet
static inline i2c_status_t i2c_bus_submit_and_wait(i2c_bus_t* bus,
                                                   i2c_packet_t* packet) {
  i2c_status_t status = i2c_bus_submit(bus, packet);
  if (status == I2C_STATUS_OK) {
    status = i2c_packet_wait(packet);
  }
  return status;
}

/*
void example() {

    i2c_bus_t* bus = i2c_bus_open(DEVICE_I2C_INSTANCE);

    static uint8_t data_out;

    static i2c_op_t ops[] = {
        {
            .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
            .size = 1,
            .data = {0x01},
        },
        {
            .flags = I2C_FLAG_RX,
            .size = sizeof(data_out),
            .ptr = &data_out,
        },
    };

    static i2c_packet_t pkt = {
        .callback = NULL,
        .context = NULL,
        .address = DEVICE_I2C_ADDRESS,
        .op_count = ARRAY_LENGTH(ops),
        .ops = ops,
        };

    status = i2c_bus_submit(bus, &pkt);

    status = i2c_packet_wait(&pkt);

    i2c_bus_close(&bus);
}
*/

#endif  // KERNEL_MODE

#endif  // TREZORHAL_I2C_BUS_H
