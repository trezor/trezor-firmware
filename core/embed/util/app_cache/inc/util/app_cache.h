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

#include <trezor_types.h>

#include <sys/systask.h>

/**
 * Spawns an external application with the given application ID.
 *
 * @param app_id Pointer to the application ID string.
 * @param app_id_size Size of the application ID string.
 * @param task_id Pointer to store the spawned application's task ID.
 *
 * @return true if the application was successfully spawned, false otherwise.
 */
bool app_cache_spawn(const char* app_id, size_t app_id_size,
                     systask_id_t* task_id);

/**
 * Kills the external application with the given task ID.
 *
 * If the application with the specified task ID is not found, the function
 * does nothing.
 *
 * @param task_id Task ID of the application
 */
void app_cache_unload(systask_id_t task_id);
