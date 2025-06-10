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

#include <sys/backup_ram.h>

#define BACKUP_RAM_HEADER_BYTES 4
#define BACKUP_RAM_MAGIC_HEADER "BRAM"
#define BACKUP_RAM_VERSION 0x0001
#define BACKUP_RAM_BASE_ADDRESS (PERIPH_BASE + 0x36400)
#define BACKUP_RAM_SIZE 0x800
#define ASSERT_IN_RANGE(x, min, max) ((x) >= (min) && (x) <= (max))

typedef union {
  uint8_t bytes[BACKUP_RAM_SIZE];
  struct {
    uint8_t header[BACKUP_RAM_HEADER_BYTES];
    uint16_t version;
    uint8_t reserved[26];
    struct {
      backup_ram_power_manager_data_t pm_data;
      // < Room for other data structures >
    } data;
    uint16_t crc;
  } storage;
} backup_ram_data_t;

// Place backup RAM data structure in the linker backup SRAM section
static backup_ram_data_t *backup_ram = NULL;

typedef struct {
  bool initialized;
  RAMCFG_HandleTypeDef hramcfg;
} backup_ram_driver_t;

static backup_ram_status_t backup_ram_consistency_check(void);
static backup_ram_status_t backup_ram_initialize_storage(void);
static uint16_t backup_ram_calculate_crc(const uint8_t *data, size_t length);
static backup_ram_status_t backup_ram_update_crc(void);
static backup_ram_status_t backup_ram_verify_crc(void);

static backup_ram_driver_t backup_ram_driver = {
    .initialized = false,
};

backup_ram_status_t backup_ram_init(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  if (drv->initialized) {
    return BACKUP_RAM_OK;
  }

  backup_ram_status_t ret = BACKUP_RAM_OK;

  // Enable backup SRAM clock
  __HAL_RCC_RAMCFG_FORCE_RESET();
  __HAL_RCC_RAMCFG_RELEASE_RESET();
  __HAL_RCC_RAMCFG_CLK_ENABLE();
  __HAL_RCC_BKPSRAM_CLK_ENABLE();

  // Clear driver instance
  memset(drv, 0, sizeof(backup_ram_driver_t));
  drv->hramcfg.Instance = RAMCFG_BKPRAM;

  HAL_StatusTypeDef hal_status = HAL_RAMCFG_Init(&drv->hramcfg);
  if (hal_status != HAL_OK) {
    goto cleanup;
  }

  // Initialize the backup RAM pointer to the actual backup RAM region
  // This is done directly with the hardware address
  backup_ram = (backup_ram_data_t *)BACKUP_RAM_BASE_ADDRESS;

  backup_ram_status_t status = backup_ram_consistency_check();
  if (status != BACKUP_RAM_OK) {
    // Backup RAM is not initialized or corrupted, initialize it
    status = backup_ram_initialize_storage();
    if (status != BACKUP_RAM_OK) {
      goto cleanup;
    }

    // Initialization ok but storage had to be reinitialized
    ret = BACKUP_RAM_OK_STORAGE_INITIALIZED;
  }

  drv->initialized = true;

  return ret;

cleanup:
  backup_ram_deinit();
  return BACKUP_RAM_ERROR;
}

void backup_ram_deinit(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  HAL_RAMCFG_DeInit(&drv->hramcfg);

  // Disable backup SRAM clock
  __HAL_RCC_BKPSRAM_CLK_DISABLE();
  __HAL_RCC_RAMCFG_CLK_DISABLE();
  backup_ram_driver.initialized = false;

  return;
}

backup_ram_status_t backup_ram_erase(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  HAL_StatusTypeDef status = HAL_RAMCFG_Erase(&drv->hramcfg);
  if (status != HAL_OK) {
    return BACKUP_RAM_ERROR;
  }

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_erase_unused(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  if (!drv->initialized) {
    return BACKUP_RAM_ERROR;
  }

  memset(backup_ram->bytes + sizeof(backup_ram->storage), 0,
         sizeof(backup_ram->bytes) - sizeof(backup_ram->storage));

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_store_power_manager_data(
    const backup_ram_power_manager_data_t *pm_data) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  if (!drv->initialized) {
    return BACKUP_RAM_ERROR;
  }

  memcpy(&backup_ram->storage.data.pm_data, pm_data,
         sizeof(backup_ram_power_manager_data_t));

  // Update CRC after writing new data
  backup_ram_update_crc();

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_read_power_manager_data(
    backup_ram_power_manager_data_t *pm_data) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  if (!drv->initialized) {
    return BACKUP_RAM_ERROR;
  }

  // Make a consistency check before reading
  backup_ram_status_t cc_status = backup_ram_consistency_check();
  if (cc_status != BACKUP_RAM_OK) {
    return cc_status;
  }

  memcpy(pm_data, (const void *)&backup_ram->storage.data.pm_data,
         sizeof(backup_ram_power_manager_data_t));

  // Assert the fuel gauge data is valid
  if (!ASSERT_IN_RANGE(pm_data->soc, 0.0f, 1.0f)) {
    return BACKUP_RAM_DATA_CHECK_ERROR;
  }

  // If SoC is equal to 0.0f, battery critical flag must be set
  if (pm_data->soc == 0.0f && !pm_data->bat_critical) {
    return BACKUP_RAM_DATA_CHECK_ERROR;
  }

  return BACKUP_RAM_OK;
}

/**
 * @brief Initialize backup RAM storage, by errasing the backup RAM completely,
 *        filling header, version and CRC.
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful.
 */
static backup_ram_status_t backup_ram_initialize_storage(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  // Erase backup RAM
  HAL_StatusTypeDef status = HAL_RAMCFG_Erase(&drv->hramcfg);
  if (status != HAL_OK) {
    return BACKUP_RAM_ERROR;
  }

  // Initialize backup RAM header
  memcpy(backup_ram->storage.header, BACKUP_RAM_MAGIC_HEADER,
         BACKUP_RAM_HEADER_BYTES);

  // Initialize version
  backup_ram->storage.version = BACKUP_RAM_VERSION;

  // Calulcate checksum of empty backup RAM
  backup_ram_update_crc();

  return BACKUP_RAM_OK;
}

/**
 * @brief Verify the consistency of the backup RAM storage
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if all consitency checks pass,
 *                             Other errors if any check fails.
 */
static backup_ram_status_t backup_ram_consistency_check(void) {
  // Check magic header
  if (memcmp(backup_ram->storage.header, BACKUP_RAM_MAGIC_HEADER,
             BACKUP_RAM_HEADER_BYTES) != 0) {
    return BACKUP_RAM_HEADER_CHECK_ERROR;
  }

  // Check version
  if (backup_ram->storage.version != BACKUP_RAM_VERSION) {
    return BACKUP_RAM_VERSION_CHECK_ERROR;
  }

  // Check CRC
  backup_ram_status_t crc_status = backup_ram_verify_crc();
  if (crc_status != BACKUP_RAM_OK) {
    return BACKUP_RAM_CRC_CHECK_ERROR;
  }

  return BACKUP_RAM_OK;
}

/**
 * @brief Calculate CRC-16-CCITT for the backup RAM storage.
 *
 * @param data Pointer to the data to calculate CRC for.
 * @param length Length of the data in bytes.
 * @return uint16_t Calculated CRC value.
 */
static uint16_t backup_ram_calculate_crc(const uint8_t *data, size_t length) {
  uint16_t crc = 0xFFFF;  // Initial value for CRC-16-CCITT

  // CRC-16-CCITT polynomial x^16 + x^12 + x^5 + 1
  const uint16_t polynomial = 0x1021;

  for (size_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t bit = 0; bit < 8; bit++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ polynomial;
      } else {
        crc = crc << 1;
      }
    }
  }

  return crc;
}

/**
 * @brief Update the CRC in the backup RAM storage.
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if successful.
 */
static backup_ram_status_t backup_ram_update_crc(void) {
  // Calculate size excluding the CRC field itself
  size_t data_size = offsetof(backup_ram_data_t, storage.crc);

  // Calculate CRC for everything in storage up to the CRC field
  uint16_t calculated_crc = backup_ram_calculate_crc(
      (const uint8_t *)&backup_ram->storage, data_size);

  // Store the calculated CRC
  backup_ram->storage.crc = calculated_crc;

  return BACKUP_RAM_OK;
}

/**
 * @brief Verify the CRC of the backup RAM storage.
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if CRC matches,
 *                             BACKUP_RAM_CRC_CHECK_ERROR if it doesn't.
 */
static backup_ram_status_t backup_ram_verify_crc(void) {
  // Calculate size excluding the CRC field itself.
  size_t data_size = offsetof(backup_ram_data_t, storage.crc);

  // Calculate CRC for everything in storage up to the CRC field.
  uint16_t calculated_crc = backup_ram_calculate_crc(
      (const uint8_t *)&backup_ram->storage, data_size);

  // Compare calculated CRC with stored CRC.
  if (backup_ram->storage.crc != calculated_crc) {
    return BACKUP_RAM_CRC_CHECK_ERROR;
  }

  return BACKUP_RAM_OK;
}

#endif  // SECURE_MODE
