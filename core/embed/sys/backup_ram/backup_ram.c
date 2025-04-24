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

// #include <trezor_types.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/backup_ram.h>

// Place backup RAM data structure in the linker backup SRAM section
__attribute__((section(".backup_ram"))) backup_ram_data_t backup_ram;

typedef struct {
  bool initialized;
  RAMCFG_HandleTypeDef hramcfg;
} backup_ram_driver_t;

static backup_ram_driver_t backup_ram_driver = {
    .initialized = false,
};

backup_ram_status_t backup_ram_init(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  if (drv->initialized) {
    return BACKUP_RAM_OK;
  }

  // Enable backup SRAM clock
  __HAL_RCC_RAMCFG_FORCE_RESET();
  __HAL_RCC_RAMCFG_RELEASE_RESET();
  __HAL_RCC_RAMCFG_CLK_ENABLE();
  __HAL_RCC_BKPSRAM_CLK_ENABLE();

  memset((void *)drv, 0, sizeof(backup_ram_driver_t));
  drv->hramcfg.Instance = RAMCFG_BKPRAM;
  HAL_StatusTypeDef status = HAL_RAMCFG_Init(&drv->hramcfg);

  if (status != HAL_OK) {
    __HAL_RCC_BKPSRAM_CLK_DISABLE();
    return BACKUP_RAM_ERROR;
  }

  drv->initialized = true;

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_deinit(void) {
  backup_ram_driver_t *drv = &backup_ram_driver;

  HAL_RAMCFG_DeInit(&drv->hramcfg);

  // Disable backup SRAM clock
  __HAL_RCC_BKPSRAM_CLK_DISABLE();
  __HAL_RCC_RAMCFG_CLK_DISABLE();
  backup_ram_driver.initialized = false;

  return BACKUP_RAM_OK;
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
  memset(backup_ram.bytes + sizeof(backup_ram.data), 0,
         sizeof(backup_ram.bytes) - sizeof(backup_ram.data));

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_store_fuel_gauge_state(
    const fuel_gauge_backup_storage_t *fg_state) {
  memcpy((void *)&backup_ram.data.fg, fg_state,
         sizeof(fuel_gauge_backup_storage_t));

  return BACKUP_RAM_OK;
}

backup_ram_status_t backup_ram_read_fuel_gauge_state(
    fuel_gauge_backup_storage_t *fg_state) {
  memcpy(fg_state, (const void *)&backup_ram.data.fg,
         sizeof(fuel_gauge_backup_storage_t));

  return BACKUP_RAM_OK;
}
