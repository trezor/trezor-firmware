
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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/backup_ram.h>
#include <sys/irq.h>

#include "../backup_ram_crc.h"

// Guard values for backup RAM slots
#define BACKUP_RAM_GUARD_OK 0xFFFF5555   // Used to mark a valid slot
#define BACKUP_RAM_GUARD_NOK 0x0000AAAA  // Used to mark an invalid slot

// Backup RAM address and configuration
#define BACKUP_RAM_BASE_ADDRESS (PERIPH_BASE + 0x36400)
#define BACKUP_RAM_SLOT_COUNT 2
#define BACKUP_RAM_SLOT_SIZE 1024
#define BACKUP_RAM_MAX_PAYLOAD_SIZE \
  (BACKUP_RAM_SLOT_SIZE - sizeof(backup_ram_payload_header_t) - 8)

// Backup RAM slot header
typedef struct {
  // Slot sequence number
  uint16_t seq;
  // Payload size in bytes
  uint16_t size;
  // Reserved for future use (must be zero)
  uint8_t reserved[4];
} backup_ram_payload_header_t;

_Static_assert(sizeof(backup_ram_payload_header_t) == 8,
               "backup_ram_slot_header_t size mismatch");

// Structure of a single backup RAM slot
typedef struct {
  // BACKUP_RAM_GUARD_xxx
  uint32_t guard;
  // CRC-16 of the header and payload
  uint16_t crc;
  // Reserved for future use (must be zero)
  uint16_t reserved;
  // Header containing metadata about the slot
  backup_ram_payload_header_t header;
  // Payload data containing TLV-encoded data
  uint8_t payload[BACKUP_RAM_MAX_PAYLOAD_SIZE];
} backup_ram_slot_t;

_Static_assert(sizeof(backup_ram_slot_t) == BACKUP_RAM_SLOT_SIZE,
               "backup_ram_slot_t size mismatch");

// g_backup_ram points to the backup RAM in peripheral memory region.
// It's more like a memory-mapped peripheral (nGnRnE) than a regular RAM region.
backup_ram_slot_t* const g_backup_ram =
    (backup_ram_slot_t*)BACKUP_RAM_BASE_ADDRESS;

#define SEQ_TO_INDEX(seq) ((seq) % BACKUP_RAM_SLOT_COUNT)

// Backup ram driver structure
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Handle of RAMCFG peripheral driver
  RAMCFG_HandleTypeDef hramcfg;
  // Next sequence number to write
  uint16_t next_seq;
  // Copy of the data in the backup RAM (if valid)
  uint8_t payload[BACKUP_RAM_MAX_PAYLOAD_SIZE];
  // Current payload size
  size_t payload_size;

} backup_ram_driver_t;

// Global driver instance
static backup_ram_driver_t g_backup_ram_driver = {.initialized = false};

// forward declarations
static void backup_ram_reload(void);
static bool is_payload_valid(const uint8_t* payload, size_t payload_size);

bool backup_ram_init(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (drv->initialized) {
    // Already initialized
    return true;
  }

  memset(drv, 0, sizeof(*drv));

  // Enable backup SRAM clock
  __HAL_RCC_RAMCFG_FORCE_RESET();
  __HAL_RCC_RAMCFG_RELEASE_RESET();
  __HAL_RCC_RAMCFG_CLK_ENABLE();
  __HAL_RCC_BKPSRAM_CLK_ENABLE();

  drv->hramcfg.Instance = RAMCFG_BKPRAM;

  HAL_StatusTypeDef hal_status = HAL_RAMCFG_Init(&drv->hramcfg);
  if (hal_status != HAL_OK) {
    drv->hramcfg.Instance = NULL;
    goto cleanup;
  }

  // Initialize storage
  backup_ram_reload();

  drv->initialized = true;
  return true;

cleanup:
  backup_ram_deinit();
  return false;
}

void backup_ram_deinit(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (drv->hramcfg.Instance != NULL) {
    HAL_RAMCFG_DeInit(&drv->hramcfg);
  }

  // Disable backup SRAM clock
  __HAL_RCC_BKPSRAM_CLK_DISABLE();
  __HAL_RCC_RAMCFG_CLK_DISABLE();

  memset(drv, 0, sizeof(*drv));
}

bool backup_ram_erase(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  memset(g_backup_ram, 0, sizeof(backup_ram_slot_t) * BACKUP_RAM_SLOT_COUNT);

  memset(drv->payload, 0, sizeof(drv->payload));
  drv->next_seq = 0;
  drv->payload_size = 0;

  irq_unlock(irq_key);

  return true;
}

static bool is_slot_valid(const backup_ram_slot_t* slot) {
  if (slot->guard != BACKUP_RAM_GUARD_OK) {
    // Invalid guard value, slot is not valid
    return false;
  }

  if (slot->reserved != 0) {
    // Reserved bytes must be zero
    return false;
  }

  if (slot->header.size > BACKUP_RAM_MAX_PAYLOAD_SIZE) {
    // Invalid reported size
    return false;
  }

  uint16_t crc = BACKUP_RAM_CRC16_INITIAL;
  crc = backup_ram_crc16(&slot->header, sizeof(slot->header), crc);
  crc = backup_ram_crc16(slot->payload, slot->header.size, crc);

  if (crc != slot->crc) {
    // CRC mismatch, slot is invalid
    return false;
  }

  if (!is_payload_valid(slot->payload, slot->header.size)) {
    // Invalid key-value pairs in the payload
    return false;
  }

  return true;
}

static void backup_ram_reload(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  int newest_seq = -1;

  // Find the newest valid slot & clear invalid slots
  for (int i = 0; i < BACKUP_RAM_SLOT_COUNT; ++i) {
    backup_ram_slot_t* slot = &g_backup_ram[i];
    if (is_slot_valid(slot) && (SEQ_TO_INDEX(slot->header.seq) == i)) {
      if (newest_seq < 0) {
        newest_seq = slot->header.seq;
      } else if ((int16_t)(slot->header.seq - newest_seq) > 0) {
        newest_seq = slot->header.seq;
      }
    } else {
      // Slot is invalid, clear it
      memset(slot, 0, sizeof(backup_ram_slot_t));
    }
  }

  memset(drv->payload, 0, sizeof(drv->payload));
  drv->payload_size = 0;
  drv->next_seq = 0;

  if (newest_seq >= 0) {
    backup_ram_slot_t* slot = &g_backup_ram[SEQ_TO_INDEX(newest_seq)];
    memcpy(drv->payload, slot->payload, slot->header.size);
    drv->payload_size = slot->header.size;
    drv->next_seq = newest_seq + 1;
  }
}

static bool backup_ram_commit(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return false;
  }

  backup_ram_payload_header_t header = {
      .seq = drv->next_seq,
      .size = drv->payload_size,
  };

  uint16_t crc = BACKUP_RAM_CRC16_INITIAL;
  crc = backup_ram_crc16(&header, sizeof(header), crc);
  crc = backup_ram_crc16(drv->payload, drv->payload_size, crc);

  volatile backup_ram_slot_t* slot = &g_backup_ram[SEQ_TO_INDEX(drv->next_seq)];

  // Invalidate the slot first
  slot->guard = BACKUP_RAM_GUARD_NOK;
  slot->crc = 0;

  // Update crc and payload header
  slot->header = header;

  // Copy the payload data
  uint32_t* src = (uint32_t*)drv->payload;
  volatile uint32_t* dst = (uint32_t*)slot->payload;
  volatile uint32_t* end = (uint32_t*)(slot->payload + drv->payload_size);
  while (dst < end) {
    *dst++ = *src++;
  }

  // Fill the rest of the slot with zeros
  end = (uint32_t*)(slot->payload + BACKUP_RAM_MAX_PAYLOAD_SIZE);
  while (dst < end) {
    *dst++ = 0;
  }

  // Make slot valid again
  slot->reserved = 0;
  slot->crc = crc;
  slot->guard = BACKUP_RAM_GUARD_OK;

  ++drv->next_seq;

  return true;
}

typedef struct {
  // Key for the item
  uint16_t key;
  // Size of the data in bytes
  uint16_t data_size;
  // Type of the item
  uint8_t item_type;
  // reserved, must be zero
  uint8_t reserved;
  // Value data (variable length, aligned to 4 bytes)
  uint8_t data[];
} backup_ram_item_t;

_Static_assert(sizeof(backup_ram_item_t) == 6,
               "backup_ram_item_t size mismatch");

#define ITEM_SIZE(data_size) \
  (sizeof(backup_ram_item_t) + ALIGN_UP(data_size, 4))

static bool is_payload_valid(const uint8_t* payload, size_t payload_size) {
  uint32_t offset = 0;

  while (offset + ITEM_SIZE(0) <= payload_size) {
    backup_ram_item_t* item = (backup_ram_item_t*)(payload + offset);
    offset += ITEM_SIZE(item->data_size);
  }

  return offset == payload_size;
}

// Find an item in the backup RAM by its key
static backup_ram_item_t* backup_ram_find_item(uint16_t key) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return NULL;
  }

  uint32_t offset = 0;

  while (offset + ITEM_SIZE(0) <= drv->payload_size) {
    backup_ram_item_t* item = (backup_ram_item_t*)(drv->payload + offset);

    if (item->key == key) {
      return item;
    }

    offset += ITEM_SIZE(item->data_size);
  }

  return NULL;
}

uint16_t backup_ram_search(uint16_t min_key) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return BACKUP_RAM_INVALID_KEY;
  }

  uint32_t offset = 0;
  uint16_t key = BACKUP_RAM_INVALID_KEY;

  while (offset + ITEM_SIZE(0) <= drv->payload_size) {
    backup_ram_item_t* item = (backup_ram_item_t*)(drv->payload + offset);

    if (item->key >= min_key && item->key < key) {
      key = item->key;
    }

    offset += ITEM_SIZE(item->data_size);
  }

  return key;
}

bool backup_ram_erase_item(uint16_t key) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  // Writing data_size==0 will just remove the item with the given key
  // Type is don't care in this case.
  bool status = backup_ram_write(key, BACKUP_RAM_ITEM_PUBLIC, NULL, 0);
  irq_unlock(irq_key);

  return status;
}

bool backup_ram_erase_protected(void) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;
  if (!drv->initialized) {
    return false;
  }

  // Lock interrupts while we mutate the in-RAM copy of the payload
  irq_key_t irq_key = irq_lock();

  uint32_t offset = 0;
  // Walk the payload buffer
  while (offset + ITEM_SIZE(0) <= drv->payload_size) {
    backup_ram_item_t* item = (backup_ram_item_t*)(drv->payload + offset);
    size_t this_size = ITEM_SIZE(item->data_size);

    if (item->item_type != BACKUP_RAM_ITEM_PUBLIC) {
      // Remove this item by sliding the remainder of the payload down over it
      uint8_t* next_item = (uint8_t*)item + this_size;
      size_t tail_bytes = drv->payload_size - (offset + this_size);
      memmove(item, next_item, tail_bytes);
      drv->payload_size -= this_size;
      // don't advance offset: new item has just been shifted into this slot
    } else {
      // keep this public item: skip over it
      offset += this_size;
    }
  }

  // write the cleaned payload back into flash-backed RAM
  bool success = backup_ram_commit();
  irq_unlock(irq_key);
  return success;
}

bool backup_ram_read(uint16_t key, void* buffer, size_t buffer_size,
                     size_t* data_size) {
  bool success = false;
  irq_key_t irq_key = irq_lock();

  backup_ram_item_t* item = backup_ram_find_item(key);

  if (data_size != NULL) {
    *data_size = item ? item->data_size : 0;
  }

  if (item == NULL) {
    goto cleanup;
  }

  if (buffer != NULL && item->data_size > buffer_size) {
    // Not enough space in the buffer
    goto cleanup;
  }

  if (buffer != NULL) {
    memcpy(buffer, item->data, item->data_size);
  }

  success = true;

cleanup:
  irq_unlock(irq_key);
  return success;
}

bool backup_ram_write(uint16_t key, backup_ram_item_type_t type,
                      const void* data, size_t data_size) {
  backup_ram_driver_t* drv = &g_backup_ram_driver;

  if (!drv->initialized) {
    return false;
  }

  if (data_size > BACKUP_RAM_MAX_KEY_DATA_SIZE) {
    // Data size exceeds maximum allowed size
    return false;
  }

  bool success = false;

  irq_key_t irq_key = irq_lock();

  backup_ram_item_t* item = backup_ram_find_item(key);

  if (item != NULL && item->item_type != type && data_size != 0) {
    // Item exists but has a different type, not supported
    goto cleanup;
  }

  if (item != NULL && item->data_size == data_size) {
    // The most common case: item exists and has the same size
    memcpy(item->data, data, data_size);
  } else {
    // Check if we have enough space for the new item
    size_t free_space = BACKUP_RAM_MAX_PAYLOAD_SIZE - drv->payload_size;

    if (item != NULL) {
      // Add the size of the existing item to the free space
      free_space += ITEM_SIZE(item->data_size);
    }

    if (ITEM_SIZE(data_size) > free_space) {
      // Not enough space for the new item
      goto cleanup;
    }

    // Remove the item if it exists
    if (item != NULL) {
      size_t deleted_size = ITEM_SIZE(item->data_size);
      uint8_t* next_item = (uint8_t*)item + deleted_size;
      uint8_t* end_of_payload = drv->payload + drv->payload_size;
      assert(next_item <= end_of_payload);
      memmove(item, next_item, end_of_payload - next_item);
      drv->payload_size -= deleted_size;
    }

    // Add a new item at the end of the payload
    if (data_size > 0) {
      item = (backup_ram_item_t*)&drv->payload[drv->payload_size];
      item->key = key;
      item->data_size = data_size;
      item->item_type = type;
      item->reserved = 0;
      memcpy(item->data, data, data_size);
      memset(&item->data[data_size], 0, ALIGN_UP(data_size, 4) - data_size);
      drv->payload_size += ITEM_SIZE(data_size);
    }
  }

  // Commit the changes to backup RAM
  success = backup_ram_commit();

cleanup:
  irq_unlock(irq_key);
  return success;
}

bool backup_ram_kernel_accessible(uint16_t key) {
  return (key == BACKUP_RAM_KEY_PM_RECOVERY ||
          key == BACKUP_RAM_KEY_BLE_SETTINGS);
}

#endif  // SECURE_MODE
