/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef TREZORHAL_TOUCH_H
#define TREZORHAL_TOUCH_H

#include <stdint.h>

#define TOUCH_START (1U << 24)
#define TOUCH_MOVE  (2U << 24)
#define TOUCH_END   (4U << 24)

#define TOUCH_ADDRESS (0x38U << 1) // the HAL requires the 7-bit address to be shifted by one bit
#define TOUCH_PACKET_SIZE 7U
#define EVENT_PRESS_DOWN 0x00U
#define EVENT_CONTACT 0x80U
#define EVENT_LIFT_UP 0x40U
#define EVENT_NO_EVENT 0xC0U
#define GESTURE_NO_GESTURE 0x00U
#define X_POS_MSB (touch_data[3] & 0xFU)
#define X_POS_LSB (touch_data[4])
#define Y_POS_MSB (touch_data[5] & 0xFU)
#define Y_POS_LSB (touch_data[6])
#define X_Y_POS ((X_POS_MSB << 20) | (X_POS_LSB << 12) | (Y_POS_MSB << 8) | (Y_POS_LSB))

void touch_init(void);
uint32_t touch_read(void);
uint32_t touch_click(void);

#endif
