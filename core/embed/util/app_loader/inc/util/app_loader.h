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

#include <util/app_cache.h>

#ifdef KERNEL_MODE

/**
 * Initializes the app cache subsystem.
 *
 * @return true on success, false on failure.
 */
bool app_loader_init(void);

#endif

/**
 * Spawns an external application with the given application ID.
 *
 * @param hash Pointer to the application hash.
 * @param task_id Pointer to store the spawned application's task ID.
 *
 * @return true if the application was successfully spawned, false otherwise.
 */
bool app_task_spawn(const app_hash_t* hash, systask_id_t* task_id);

/**
 * Checks if an application is currently running.
 */
bool app_task_is_running(systask_id_t task_id);

/**
 * Retrieves postmortem information for a terminated application.
 *
 * If the application is still running, the info structure will be invalid.
 *
 * @param task_id The system task identifier of the application.
 * @param info Pointer to a structure to receive postmortem information.
 * @return true if postmortem information was retrieved, false otherwise.
 */
bool app_task_get_pminfo(systask_id_t task_id, systask_postmortem_t* pminfo);

/**
 * Unloads an application and frees all associated resources.
 *
 * When an application is unloaded the task_id becomes invalid and
 * cannot be used in subsequent calls to app_task_is_running() or other
 * functions.
 *
 * @param task_id The system task identifier of the application to unload.
 */
void app_task_unload(systask_id_t task_id);
