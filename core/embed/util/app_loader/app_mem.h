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

#pragma once

/**
 * Allocates memory for an application.
 *
 * @param size The size of the memory to allocate in bytes.
 *
 * @return Pointer to the allocated memory, or NULL if allocation failed.
 */
void* app_mem_alloc(size_t size);

/**
 * Frees memory previously allocated with app_mem_alloc().
 *
 * @param ptr Pointer to the memory to free.
 */
void app_mem_free(void* ptr);
