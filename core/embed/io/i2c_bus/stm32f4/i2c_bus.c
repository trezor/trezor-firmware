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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/i2c_bus.h>

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef KERNEL_MODE

// I2C bus SCL clock frequency
#define I2C_BUS_SCL_FREQ 200000  // Hz

// We expect the I2C bus to be running at ~200kHz
// and max response time of the device is 1000us
#define I2C_BUS_CHAR_TIMEOUT (50 + 5)  // us
#define I2C_BUS_OP_TIMEOUT 1000        // us

#define I2C_BUS_TIMEOUT(n) \
  ((I2C_BUS_CHAR_TIMEOUT * (1 + n) + I2C_BUS_OP_TIMEOUT + 999) / 1000)

// I2C bus hardware definition
typedef struct {
  // I2C controller registers
  I2C_TypeDef* regs;
  // SCL pin GPIO port
  GPIO_TypeDef* scl_port;
  // SDA pin GPIO port
  GPIO_TypeDef* sda_port;
  // SCL pin number
  uint16_t scl_pin;
  // SDA pin number
  uint16_t sda_pin;
  // Alternate function for SCL and SDA pins
  uint8_t pin_af;
  // Register for I2C controller reset
  volatile uint32_t* reset_reg;
  // Reset bit specific for this I2C controller
  uint32_t reset_bit;
  // I2C event IRQ number
  uint32_t ev_irq;
  // I2C error IRQ number
  uint32_t er_irq;
  // Guard time [us] between STOP and START condition.
  // If zero, the guard time is not used.
  uint16_t guard_time;
} i2c_bus_def_t;

// I2C bus hardware definitions
static const i2c_bus_def_t g_i2c_bus_def[I2C_COUNT] = {
    {
        .regs = I2C_INSTANCE_0,
        .scl_port = I2C_INSTANCE_0_SCL_PORT,
        .sda_port = I2C_INSTANCE_0_SDA_PORT,
        .scl_pin = I2C_INSTANCE_0_SCL_PIN,
        .sda_pin = I2C_INSTANCE_0_SDA_PIN,
        .pin_af = I2C_INSTANCE_0_PIN_AF,
        .reset_reg = I2C_INSTANCE_0_RESET_REG,
        .reset_bit = I2C_INSTANCE_0_RESET_BIT,
        .ev_irq = I2C_INSTANCE_0_EV_IRQn,
        .er_irq = I2C_INSTANCE_0_ER_IRQn,
        .guard_time = I2C_INSTANCE_0_GUARD_TIME,
    },
#ifdef I2C_INSTANCE_1
    {
        .regs = I2C_INSTANCE_1,
        .scl_port = I2C_INSTANCE_1_SCL_PORT,
        .sda_port = I2C_INSTANCE_1_SDA_PORT,
        .scl_pin = I2C_INSTANCE_1_SCL_PIN,
        .sda_pin = I2C_INSTANCE_1_SDA_PIN,
        .pin_af = I2C_INSTANCE_1_PIN_AF,
        .reset_reg = I2C_INSTANCE_1_RESET_REG,
        .reset_bit = I2C_INSTANCE_1_RESET_BIT,
        .ev_irq = I2C_INSTANCE_1_EV_IRQn,
        .er_irq = I2C_INSTANCE_1_ER_IRQn,
        .guard_time = I2C_INSTANCE_1_GUARD_TIME,
    },
#endif
#ifdef I2C_INSTANCE_2
    {
        .regs = I2C_INSTANCE_2,
        .scl_port = I2C_INSTANCE_2_SCL_PORT,
        .sda_port = I2C_INSTANCE_2_SDA_PORT,
        .scl_pin = I2C_INSTANCE_2_SCL_PIN,
        .sda_pin = I2C_INSTANCE_2_SDA_PIN,
        .pin_af = I2C_INSTANCE_2_PIN_AF,
        .reset_reg = I2C_INSTANCE_2_RESET_REG,
        .reset_bit = I2C_INSTANCE_2_RESET_BIT,
        .ev_irq = I2C_INSTANCE_2_EV_IRQn,
        .er_irq = I2C_INSTANCE_2_ER_IRQn,
        .guard_time = I2C_INSTANCE_2_GUARD_TIME,
    },
#endif
};

struct i2c_bus {
  // Number of references to the bus
  // (0 means the bus is not initialized)
  uint32_t refcount;

  // Hardware definition
  const i2c_bus_def_t* def;

  // Timer for timeout handling
  systimer_t* timer;

  // Head of the packet queue
  // (this packet is currently being processed)
  i2c_packet_t* queue_head;
  // Tail of the packet queue
  // (this packet is the last in the queue)
  i2c_packet_t* queue_tail;

  // Next operation index in the current packet
  // == 0 => no operation is being processed
  // == queue_head->op_count => no more operations
  int next_op;

  // Current operation address byte
  uint8_t addr_byte;
  // Points to the data buffer of the current operation
  uint8_t* buff_ptr;
  // Remaining number of bytes of the buffer to transfer
  uint16_t buff_size;
  // Remaining number of bytes of the current operation
  // (if the transfer is split into multiple operations it
  //  may be different from buff_size)
  uint16_t transfer_size;
  // For case of split transfer, points to the next operation
  // that is part of the current transfer
  int transfer_op;

  // Set if the STOP condition is requested after the current operation
  // when data transfer is completed.
  bool stop_requested;
  // Set if pending transaction is being aborted
  bool abort_pending;

  // Flag indicating that the completion callback is being executed
  bool callback_executed;

  // The last time [us] the STOP condition was issued
  uint64_t stop_time;
};

// I2C bus driver instances
static i2c_bus_t g_i2c_bus_driver[I2C_COUNT] = {0};

// Check if the I2C bus pointer is valid
static inline bool i2c_bus_ptr_valid(const i2c_bus_t* bus) {
  if (bus >= &g_i2c_bus_driver[0] && bus < &g_i2c_bus_driver[I2C_COUNT]) {
    uintptr_t offset = (uintptr_t)bus - (uintptr_t)&g_i2c_bus_driver[0];
    if (offset % sizeof(i2c_bus_t) == 0) {
      return bus->refcount > 0;
    }
  }
  return false;
}

// forward declarations
static void i2c_bus_timer_callback(void* context);
static void i2c_bus_head_continue(i2c_bus_t* bus);

static void i2c_bus_unlock(i2c_bus_t* bus) {
  const i2c_bus_def_t* def = bus->def;

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // Set SDA and SCL high
  HAL_GPIO_WritePin(def->sda_port, def->sda_pin, GPIO_PIN_SET);
  HAL_GPIO_WritePin(def->scl_port, def->scl_pin, GPIO_PIN_SET);

  // Configure SDA and SCL as open-drain output
  // and connect to the I2C peripheral
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Pin = def->scl_pin;
  HAL_GPIO_Init(def->scl_port, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = def->sda_pin;
  HAL_GPIO_Init(def->sda_port, &GPIO_InitStructure);

  uint32_t clock_count = 16;

  while ((HAL_GPIO_ReadPin(def->sda_port, def->sda_pin) == GPIO_PIN_RESET) &&
         (clock_count-- > 0)) {
    // Clock SCL
    HAL_GPIO_WritePin(def->scl_port, def->scl_pin, GPIO_PIN_RESET);
    systick_delay_us(10);
    HAL_GPIO_WritePin(def->scl_port, def->scl_pin, GPIO_PIN_SET);
    systick_delay_us(10);
  }
}

static void i2c_bus_reset(i2c_bus_t* bus) {
  const i2c_bus_def_t* def = bus->def;

  // Reset I2C peripheral
  *def->reset_reg |= def->reset_bit;
  *def->reset_reg &= ~def->reset_bit;

  I2C_TypeDef* regs = def->regs;

  // Configure I2C peripheral

  uint32_t pclk_hz = HAL_RCC_GetPCLK1Freq();
  uint32_t pclk_mhz = I2C_FREQRANGE(pclk_hz);
  uint32_t i2c_speed_hz = I2C_BUS_SCL_FREQ;

  regs->CR1 = 0;
  regs->TRISE = I2C_RISE_TIME(pclk_mhz, i2c_speed_hz);
  regs->CR2 = pclk_mhz;
  regs->CCR = I2C_SPEED(pclk_hz, i2c_speed_hz, I2C_DUTYCYCLE_16_9);
  regs->FLTR = 0;
  regs->OAR1 = 0;
  regs->OAR2 = 0;
  regs->CR1 |= I2C_CR1_PE;
}

static void i2c_bus_deinit(i2c_bus_t* bus) {
  const i2c_bus_def_t* def = bus->def;

  systimer_delete(bus->timer);

  if (bus->def == NULL) {
    return;
  }

  NVIC_DisableIRQ(def->ev_irq);
  NVIC_DisableIRQ(def->er_irq);

  I2C_TypeDef* regs = def->regs;

  // Disable I2C peripheral
  regs->CR1 = 0;

  // Reset I2C peripheral
  *def->reset_reg |= def->reset_bit;
  *def->reset_reg &= ~def->reset_bit;

  bus->def = NULL;
}

static bool i2c_bus_init(i2c_bus_t* bus, int bus_index) {
  memset(bus, 0, sizeof(i2c_bus_t));

  switch (bus_index) {
    case 0:
      // enable I2C clock
      I2C_INSTANCE_0_CLK_EN();
      I2C_INSTANCE_0_SCL_CLK_EN();
      I2C_INSTANCE_0_SDA_CLK_EN();
      break;

#ifdef I2C_INSTANCE_1
    case 1:
      I2C_INSTANCE_1_CLK_EN();
      I2C_INSTANCE_1_SCL_CLK_EN();
      I2C_INSTANCE_1_SDA_CLK_EN();
      break;
#endif

#ifdef I2C_INSTANCE_2
    case 2:
      I2C_INSTANCE_2_CLK_EN();
      I2C_INSTANCE_2_SCL_CLK_EN();
      I2C_INSTANCE_2_SDA_CLK_EN();
      break;
#endif
    default:
      goto cleanup;
  }

  const i2c_bus_def_t* def = &g_i2c_bus_def[bus_index];

  bus->def = def;

  // Unlocks potentially locked I2C bus by
  // generating several clock pulses on SCL while SDA is low
  i2c_bus_unlock(bus);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // Configure SDA and SCL as open-drain output
  // and connect to the I2C peripheral
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Alternate = def->pin_af;
  GPIO_InitStructure.Pin = def->scl_pin;
  HAL_GPIO_Init(def->scl_port, &GPIO_InitStructure);

  GPIO_InitStructure.Alternate = def->pin_af;
  GPIO_InitStructure.Pin = def->sda_pin;
  HAL_GPIO_Init(def->sda_port, &GPIO_InitStructure);

  i2c_bus_reset(bus);

  NVIC_SetPriority(def->ev_irq, IRQ_PRI_NORMAL);
  NVIC_SetPriority(def->er_irq, IRQ_PRI_NORMAL);

  NVIC_EnableIRQ(def->ev_irq);
  NVIC_EnableIRQ(def->er_irq);

  bus->timer = systimer_create(i2c_bus_timer_callback, bus);
  if (bus->timer == NULL) {
    goto cleanup;
  }

  return true;

cleanup:
  i2c_bus_deinit(bus);
  return false;
}

i2c_bus_t* i2c_bus_open(uint8_t bus_index) {
  if (bus_index >= I2C_COUNT) {
    return NULL;
  }

  i2c_bus_t* bus = &g_i2c_bus_driver[bus_index];

  if (bus->refcount == 0) {
    if (!i2c_bus_init(bus, bus_index)) {
      return NULL;
    }
  }

  ++bus->refcount;

  return bus;
}

void i2c_bus_close(i2c_bus_t* bus) {
  if (!i2c_bus_ptr_valid(bus)) {
    return;
  }

  if (bus->refcount > 0) {
    if (--bus->refcount == 0) {
      i2c_bus_deinit(bus);
    }
  }
}

i2c_status_t i2c_packet_status(const i2c_packet_t* packet) {
  irq_key_t irq_key = irq_lock();
  i2c_status_t status = packet->status;
  irq_unlock(irq_key);
  return status;
}

i2c_status_t i2c_packet_wait(const i2c_packet_t* packet) {
  while (true) {
    i2c_status_t status = i2c_packet_status(packet);

    if (status != I2C_STATUS_PENDING) {
      return status;
    }

    // Enter sleep mode and wait for any interrupt
    __WFI();
  }
}

// Invokes the packet completion callback
static inline void i2c_bus_invoke_callback(i2c_bus_t* bus, i2c_packet_t* packet,
                                           i2c_status_t status) {
  packet->status = status;
  if (packet->callback) {
    bus->callback_executed = true;
    packet->callback(packet->context, packet);
    bus->callback_executed = false;
  }
}

// Appends the packet to the end of the queue
// Returns true if the queue was empty before
// Expects disabled IRQ or calling from IRQ context
static inline bool i2c_bus_add_packet(i2c_bus_t* bus, i2c_packet_t* packet) {
  if (bus->queue_tail == NULL) {
    bus->queue_head = packet;
    bus->queue_tail = packet;
    return true;
  } else {
    bus->queue_tail->next = packet;
    bus->queue_tail = packet;
    return false;
  }
}

// Removes the packet from the queue (if present)
// Returns true if the removed we removed head of the queue
// Expects disabled IRQ or calling from IRQ context
static inline bool i2c_bus_remove_packet(i2c_bus_t* bus, i2c_packet_t* packet) {
  if (packet == bus->queue_head) {
    // Remove head of the queue
    bus->queue_head = packet->next;
    // If the removed packet was also the tail, reset the tail
    if (bus->queue_tail == packet) {
      bus->queue_tail = NULL;
    }
    packet->next = NULL;
    return true;
  }

  // Remove from the middle or tail of the queue
  i2c_packet_t* p = bus->queue_head;
  while (p->next != NULL && p->next != packet) {
    p = p->next;
  }

  if (p->next == packet) {
    // The packet found in the queue, remove it
    p->next = packet->next;
    // Update the tail if necessary
    if (bus->queue_tail == packet) {
      bus->queue_tail = p;
    }
    packet->next = NULL;
  }

  return false;
}

i2c_status_t i2c_bus_submit(i2c_bus_t* bus, i2c_packet_t* packet) {
  if (!i2c_bus_ptr_valid(bus) || packet == NULL) {
    // Invalid bus or packet
    return I2C_STATUS_ERROR;
  }

  if (packet->next != NULL) {
    // Packet is already queued
    return I2C_STATUS_ERROR;
  }

  packet->status = I2C_STATUS_PENDING;

  // Insert packet into the queue
  irq_key_t irq_key = irq_lock();
  if (i2c_bus_add_packet(bus, packet)) {
    // The queue was empty, start the operation
    if (!bus->callback_executed && !bus->abort_pending) {
      i2c_bus_head_continue(bus);
    }
  }
  irq_unlock(irq_key);

  return I2C_STATUS_OK;
}

void i2c_bus_abort(i2c_bus_t* bus, i2c_packet_t* packet) {
  if (!i2c_bus_ptr_valid(bus) || packet == NULL) {
    // Invalid bus or packet
    return;
  }

  irq_key_t irq_key = irq_lock();

  if (packet->status == I2C_STATUS_PENDING) {
    if (i2c_bus_remove_packet(bus, packet) && bus->next_op > 0) {
      // The packet was being processed

      // Reset internal state
      bus->next_op = 0;
      bus->buff_ptr = NULL;
      bus->buff_size = 0;
      bus->transfer_size = 0;
      bus->transfer_op = 0;

      // Inform interrupt handler about pending abort
      bus->abort_pending = true;
      bus->stop_requested = true;

      // Abort operation may fail if the bus is busy or noisy
      // so we need to set a timeout.
      systimer_set(bus->timer, I2C_BUS_TIMEOUT(2));
    }
    packet->status = I2C_STATUS_ABORTED;
  }

  irq_unlock(irq_key);
}

// Completes the current packet by removing it from the queue
// an invoking the completion callback
//
// Must be called with IRQ disabled or from IRQ context
// Expects the operation is finished
static void i2c_bus_head_complete(i2c_bus_t* bus, i2c_status_t status) {
  i2c_packet_t* packet = bus->queue_head;
  if (packet != NULL) {
    // Remove packet from the queue
    i2c_bus_remove_packet(bus, packet);

    // Reset internal state
    bus->next_op = 0;
    bus->buff_ptr = NULL;
    bus->buff_size = 0;
    bus->transfer_size = 0;
    bus->transfer_op = 0;
    bus->abort_pending = false;

    systimer_unset(bus->timer);

    // Invoke the completion callback
    i2c_bus_invoke_callback(bus, packet, status);
  }
}

// Starts the next operation in the packet by
// programming the I2C controller
//
// Must be called with IRQ disabled or from IRQ context
// Expects no other operation is being processed
static void i2c_bus_head_continue(i2c_bus_t* bus) {
  I2C_TypeDef* regs = bus->def->regs;

  if (bus->stop_requested) {
    // Issue STOP condition
    regs->CR1 |= I2C_CR1_STOP;
    if (bus->def->guard_time > 0) {
      bus->stop_time = systick_us();
    }
    bus->stop_requested = false;
  }

  if (bus->abort_pending) {
    systimer_unset(bus->timer);
    bus->abort_pending = false;
  }

  // Check if the bus is in a faulty state
  if (bus->queue_head != NULL && bus->next_op == 0) {
    uint32_t sr2 = regs->SR2;

    if ((sr2 & I2C_SR2_BUSY) && ((sr2 & I2C_SR2_MSL) == 0)) {
      // the bus is busy but not in master mode.
      // It may happen if in case of noise or other issues.
      i2c_bus_reset(bus);
    }
  }

  uint32_t cr1 = regs->CR1;
  cr1 &= ~(I2C_CR1_POS | I2C_CR1_ACK | I2C_CR1_STOP | I2C_CR1_START);

  uint32_t cr2 = regs->CR2;
  cr2 &= ~(I2C_CR2_ITBUFEN | I2C_CR2_ITEVTEN | I2C_CR2_ITERREN);

  if (bus->queue_head != NULL) {
    i2c_packet_t* packet = bus->queue_head;

    if (bus->next_op < packet->op_count) {
      i2c_op_t* op = &packet->ops[bus->next_op++];

      // Get data ptr and data length
      if (op->flags & I2C_FLAG_EMBED) {
        bus->buff_ptr = op->data;
        bus->buff_size = MIN(op->size, sizeof(op->data));
      } else {
        bus->buff_ptr = op->ptr;
        bus->buff_size = op->size;
      }

      // Calculate transfer size
      bus->transfer_size = bus->buff_size;
      bus->transfer_op = bus->next_op;

      // Include following operations in the transfer if:
      // 1) We are not processing the last operation
      // 2) STOP condition is not requested in the current operation
      // 3) START condition is not requested in the next operation
      // 4) The next operation has the same direction

      while ((bus->next_op != packet->op_count) &&
             ((op->flags & I2C_FLAG_STOP) == 0) &&
             (((op + 1)->flags & I2C_FLAG_START) == 0) &&
             (((op + 1)->flags & I2C_FLAG_TX) == (op->flags & I2C_FLAG_TX))) {
        // Move to the next operation
        op = &packet->ops[bus->next_op++];

        if (op->flags & I2C_FLAG_EMBED) {
          bus->transfer_size += MIN(op->size, sizeof(op->data));
        } else {
          bus->transfer_size += op->size;
        }
      }

      // STOP condition:
      //  1) if it is explicitly requested
      //  2) if it is the last operation in the packet
      bus->stop_requested = ((op->flags & I2C_FLAG_STOP) != 0) ||
                            (bus->next_op == packet->op_count);

      // Calculate address byte
      bus->addr_byte = packet->address << 1;

      // ACK, POS, ITBUFEN flags are set based on the operation
      if (bus->transfer_size > 0) {
        if (op->flags & I2C_FLAG_TX) {
          cr2 |= I2C_CR2_ITBUFEN;
        } else if (op->flags & I2C_FLAG_RX) {
          bus->addr_byte |= 1;  // Set RW bit to 1 (READ)
          if (bus->transfer_size == 1) {
            cr2 |= I2C_CR2_ITBUFEN;
          } else if (bus->transfer_size == 2) {
            cr1 |= I2C_CR1_POS;
          } else if (bus->transfer_size == 3) {
            cr1 |= I2C_CR1_ACK;
          } else if (bus->transfer_size > 3) {
            cr2 |= I2C_CR2_ITBUFEN;
            cr1 |= I2C_CR1_ACK;
          }
        }
      }

      // Enable event and error interrupts
      cr2 |= I2C_CR2_ITEVTEN | I2C_CR2_ITERREN;

      // Generate start condition
      // (this also clears all status flags)
      cr1 |= I2C_CR1_START;

      // Each operation has its own timeout calculated
      // based on the number of bytes to transfer and the bus speed +
      // expected operation overhead
      systimer_set(bus->timer,
                   I2C_BUS_TIMEOUT(bus->transfer_size) + packet->timeout);

      // Guard time between operations STOP and START condition
      if (bus->def->guard_time > 0) {
        // Add 5us as a safety margin since the stop_time was set before the
        // STOP condition was issued
        uint16_t guard_time = bus->def->guard_time + 5;
        while (systick_us() - bus->stop_time < guard_time)
          ;
      }
    }

    // Clear BTF flag
    (void)regs->DR;
  }

  regs->CR1 = cr1;
  regs->CR2 = cr2;
}

// Timer callback handling I2C bus timeout
static void i2c_bus_timer_callback(void* context) {
  i2c_bus_t* bus = (i2c_bus_t*)context;

  if (bus->abort_pending) {
    // This may be caused by the bus being busy/noisy.
    // Reset I2C Controller
    i2c_bus_reset(bus);
    // Start the next packet
    i2c_bus_head_continue(bus);
  } else {
    // Timeout during normal operation occurred
    i2c_packet_t* packet = bus->queue_head;
    if (packet != NULL) {
      // Determine the status based on the current bus state
      I2C_TypeDef* regs = bus->def->regs;
      i2c_status_t status;

      if ((regs->CR1 & I2C_CR1_START) && (regs->SR2 & I2C_SR2_BUSY)) {
        // START condition was issued but the bus is still busy
        status = I2C_STATUS_BUSY;
      } else {
        status = I2C_STATUS_TIMEOUT;
      }

      // Abort pending packet
      i2c_bus_abort(bus, packet);
      // Invoke the completion callback
      i2c_bus_invoke_callback(bus, packet, status);
    }
  }
}

static uint8_t i2c_bus_read_buff(i2c_bus_t* bus) {
  if (bus->transfer_size > 0) {
    while (bus->buff_size == 0 && bus->transfer_op < bus->next_op) {
      i2c_op_t* op = &bus->queue_head->ops[bus->transfer_op++];
      if (op->flags & I2C_FLAG_EMBED) {
        bus->buff_ptr = op->data;
        bus->buff_size = MIN(op->size, sizeof(op->data));
      } else {
        bus->buff_ptr = op->ptr;
        bus->buff_size = op->size;
      }
    }

    --bus->transfer_size;

    if (bus->buff_size > 0) {
      --bus->buff_size;
      return *bus->buff_ptr++;
    }
  }

  return 0;
}

static void i2c_bus_write_buff(i2c_bus_t* bus, uint8_t data) {
  if (bus->transfer_size > 0) {
    while (bus->buff_size == 0 && bus->transfer_op < bus->next_op) {
      i2c_op_t* op = &bus->queue_head->ops[bus->transfer_op++];
      if (op->flags & I2C_FLAG_EMBED) {
        bus->buff_ptr = op->data;
        bus->buff_size = MIN(op->size, sizeof(op->data));
      } else {
        bus->buff_ptr = op->ptr;
        bus->buff_size = op->size;
      }
    }

    --bus->transfer_size;

    if (bus->buff_size > 0) {
      *bus->buff_ptr++ = data;
      --bus->buff_size;
    }
  }
}

// I2C bus event interrupt handler
static void i2c_bus_ev_handler(i2c_bus_t* bus) {
  I2C_TypeDef* regs = bus->def->regs;

  uint32_t sr1 = regs->SR1;

  if (sr1 & I2C_SR1_SB) {
    // START condition generated
    // Send the address byte
    regs->DR = bus->addr_byte;
    // Operation cannot be aborted at this point.
    // We need to wait for ADDR flag.
  } else if (sr1 & I2C_SR1_ADDR) {
    // Address sent and ACKed by the slave
    // By reading SR2 we clear ADDR flag and start the data transfer
    regs->SR2;

    if (bus->abort_pending) {
      // Only TX operation can be aborted at this point
      // For RX operation, we need to wait for the first byte
      if ((bus->addr_byte & 1) == 0) {
        // Issue STOP condition and start the next packet
        i2c_bus_head_continue(bus);
      }
    } else if (bus->transfer_size == 0) {
      // Operation contains only address without any data
      if (bus->next_op == bus->queue_head->op_count) {
        i2c_bus_head_complete(bus, I2C_STATUS_OK);
      }
      i2c_bus_head_continue(bus);
    }
  } else if ((bus->addr_byte & 1) == 0) {
    // Data transmit phase
    if (bus->abort_pending) {
      // Issue STOP condition and start the next packet
      i2c_bus_head_continue(bus);
    } else if ((sr1 & I2C_SR1_TXE) && (regs->CR2 & I2C_CR2_ITBUFEN)) {
      // I2C controller transmit buffer is empty.
      // The interrupt flag is cleared by writing the DR register.
      if (bus->transfer_size > 0) {
        // Send the next byte
        regs->DR = i2c_bus_read_buff(bus);
        if (bus->transfer_size == 0) {
          // All data bytes were transmitted
          // Disable RXNE interrupt and wait for BTF
          regs->CR2 &= ~I2C_CR2_ITBUFEN;
        }
      }
    } else if (sr1 & I2C_SR1_BTF) {
      if (bus->transfer_size == 0) {
        // All data bytes were shifted out
        if (bus->next_op == bus->queue_head->op_count) {
          // Last operation in the packet
          i2c_bus_head_complete(bus, I2C_STATUS_OK);
        }
        i2c_bus_head_continue(bus);
      }
    }
  } else {  // Data receive phase
    if (bus->abort_pending) {
      regs->CR1 &= ~(I2C_CR1_ACK | I2C_CR1_POS);
      (void)regs->DR;
      // Issue STOP condition and start the next packet
      i2c_bus_head_continue(bus);
    } else if ((sr1 & I2C_SR1_RXNE) && (regs->CR2 & I2C_CR2_ITBUFEN)) {
      uint8_t received_byte = regs->DR;
      if (bus->transfer_size > 0) {
        // Receive the next byte
        i2c_bus_write_buff(bus, received_byte);
        if (bus->transfer_size == 3) {
          // 3 bytes left to receive
          // Disable RXNE interrupt and wait for BTF
          regs->CR2 &= ~I2C_CR2_ITBUFEN;
        } else if (bus->transfer_size == 0) {
          // All data bytes were received
          // We get here only in case of 1 byte transfers
          if (bus->next_op == bus->queue_head->op_count) {
            // Last operation in the packet
            i2c_bus_head_complete(bus, I2C_STATUS_OK);
          }
          i2c_bus_head_continue(bus);
        }
      }
    } else if (sr1 & I2C_SR1_BTF) {
      if (bus->transfer_size == 3) {
        // 3 bytes left to receive
        regs->CR1 &= ~I2C_CR1_ACK;
        i2c_bus_write_buff(bus, regs->DR);
      } else if (bus->transfer_size == 2) {
        // 2 left bytes are already in DR a shift register
        if (bus->stop_requested) {
          // Issue STOP condition before reading the 2 last bytes
          regs->CR1 |= I2C_CR1_STOP;
          if (bus->def->guard_time > 0) {
            bus->stop_time = systick_us();
          }
          bus->stop_requested = false;
        }
        i2c_bus_write_buff(bus, regs->DR);
        i2c_bus_write_buff(bus, regs->DR);

        if (bus->next_op == bus->queue_head->op_count) {
          i2c_bus_head_complete(bus, I2C_STATUS_OK);
        }
        i2c_bus_head_continue(bus);
      }
    }
  }
}

// I2C bus error interrupt handler
static void i2c_bus_er_handler(i2c_bus_t* bus) {
  I2C_TypeDef* regs = bus->def->regs;

  uint32_t sr1 = regs->SR1;

  // Clear error flags
  regs->SR1 &= ~(I2C_SR1_AF | I2C_SR1_ARLO | I2C_SR1_BERR);

  if (sr1 & I2C_SR1_AF) {
    // NACK received
    if (bus->abort_pending) {
      // Start the next packet
      i2c_bus_head_continue(bus);
    } else if (bus->next_op > 0) {
      // Complete packet with error
      i2c_bus_head_complete(bus, I2C_STATUS_NACK);
      // Issue stop condition and start the next packet
      bus->stop_requested = true;
      i2c_bus_head_continue(bus);
    } else {
      // Invalid state
    }
  }

  if (sr1 & I2C_SR1_ARLO) {
    if (bus->abort_pending) {
      // Packet aborted or invalid state
      // Start the next packet
      bus->stop_requested = false;
      i2c_bus_head_continue(bus);
    } else if (bus->next_op > 0) {
      // Arbitration lost, complete packet with error
      i2c_bus_head_complete(bus, I2C_STATUS_ERROR);
      // Start the next packet
      bus->stop_requested = false;
      i2c_bus_head_continue(bus);
    }
  }

  if (sr1 & I2C_SR1_BERR) {
    // Bus error
    // Ignore and continue with pending operation
  }
}

// Interrupt handlers

#ifdef I2C_INSTANCE_0
void I2C_INSTANCE_0_EV_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_ev_handler(&g_i2c_bus_driver[0]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

void I2C_INSTANCE_0_ER_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_er_handler(&g_i2c_bus_driver[0]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif

#ifdef I2C_INSTANCE_1
void I2C_INSTANCE_1_EV_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_ev_handler(&g_i2c_bus_driver[1]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

void I2C_INSTANCE_1_ER_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_er_handler(&g_i2c_bus_driver[1]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif

#ifdef I2C_INSTANCE_2
void I2C_INSTANCE_2_EV_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_ev_handler(&g_i2c_bus_driver[2]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

void I2C_INSTANCE_2_ER_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  i2c_bus_er_handler(&g_i2c_bus_driver[2]);
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif

#endif  // KERNEL_MODE
