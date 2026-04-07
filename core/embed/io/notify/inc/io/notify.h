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

/**
 * @file notify.h
 * @brief Device-to-host push notification system
 *
 * This module provides functionality for sending push notifications from the
 * Trezor device to a connected host. It allows the device to proactively
 * communicate status changes, events, and other important information without
 * waiting for host requests.
 */

#pragma once

#include <trezor_types.h>

/**
 * @brief Enumeration of notification event types
 *
 * Defines the various types of events that can trigger push notifications
 * from the device to the connected host.
 */

typedef enum {
  NOTIFY_BOOT = 0,       /**< Device boot/startup notification */
  NOTIFY_UNLOCK = 1,     /**< Device unlocked and ready to accept messages */
  NOTIFY_LOCK = 2,       /**< Device hard-locked and won't accept messages */
  NOTIFY_DISCONNECT = 3, /**< User-initiated disconnect from host */
  NOTIFY_SETTING_CHANGE = 4, /**< Change of settings */
  NOTIFY_SOFTLOCK =
      5, /**< Device soft-locked (e.g., after clicking power button) */
  NOTIFY_SOFTUNLOCK =
      6, /**< Device soft-unlocked (e.g., after successful pin entry) */
  NOTIFY_PIN_CHANGE = 7, /**< Pin changed on the device */
  NOTIFY_WIPE = 8,       /**< Factory reset (wipe) invoked */
  NOTIFY_UNPAIR = 9,     /**< BLE bonding for current connection deleted */
  NOTIFY_POWER_STATUS_CHANGE =
      10, /**< Power status changed, i.e. charging started */
  // Additional notification types can be added here as needed
} notification_event_t;

/**
 * @brief Notification data structure
 *
 * Contains the event type and associated flags/data that will be sent
 * to the host as part of the push notification.
 */
typedef struct {
  uint8_t version; /**< Version of the notification data structure */
  uint8_t event;   /**< Event type from notification_event_t enum */

  /**
   * @brief Event-specific flags and data
   *
   * Union allows for flexible data representation - can be accessed
   * as structured flags or as a single byte value.
   */
  union {
    /**
     * @brief Structured flag representation
     *
     * Provides bit-level access to individual flags within the data byte.
     */
    struct {
      uint8_t bootloader : 1; /**< Set if device is in bootloader mode */
      uint8_t reserved : 7;   /**< Reserved bits for future use */
    } flags;

    uint8_t all_flags; /**< Raw byte access to all flags */
  } flags;

} notification_data_t;

/**
 * @brief Send a push notification to the connected host
 *
 * Transmits a notification event to the host, allowing the device to
 * proactively communicate status changes or important events.
 *
 * @param event The type of notification event to send
 *
 * @note This function handles the underlying communication protocol
 *       and data formatting automatically based on the event type.
 */
void notify_send(notification_event_t event);
