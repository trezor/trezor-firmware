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

#include <sec/backup_ram.h>

bool backup_ram_init(void) { return true; }
void backup_ram_deinit(void) {}

bool backup_ram_erase(void) { return true; }

bool backup_ram_erase_protected(void) { return true; }

bool backup_ram_erase_item(uint16_t key) { return false; }

uint16_t backup_ram_search(uint16_t min_key) { return BACKUP_RAM_INVALID_KEY; }

bool backup_ram_write(uint16_t key, backup_ram_item_type_t type,
                      const void* data, size_t data_size) {
  return false;
}

bool backup_ram_read(uint16_t key, void* buffer, size_t buffer_size,
                     size_t* data_size) {
  return false;
}

bool backup_ram_kernel_accessible(uint16_t key) { return false; }
