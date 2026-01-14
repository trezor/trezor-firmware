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

#ifdef KERNEL

#include <sys/systask.h>

/** Applet structure */
typedef struct applet applet_t;

/** Applet privileges */
typedef struct {
  bool assets_area_access;
} applet_privileges_t;

/** Callback called when an applet is unloaded */
typedef void (*applet_unload_cb_t)(applet_t* applet);

struct applet {
  /** Applet privileges */
  applet_privileges_t privileges;

  /** Task associated with the applet */
  systask_t task;
  /** Callback called when the applet is unloaded */
  applet_unload_cb_t unload_cb;

#ifdef TREZOR_EMULATOR
  /** Handle returned by `dlopen()` */
  void* handle;
#else
  /** Applet memory layout describing the memory areas
   * the applet is allowed to use */
  applet_layout_t layout;
#endif
};

/**
 * @brief Initializes the applet structure
 *
 * Does just basic initialization of the applet structure without
 * initializing the task associated with the applet.
 *
 * @param applet Pointer to the applet to initialize.
 * @param privileges Pointer to the applet privileges.
 * @param unload_cb Callback called when the applet is unloaded.
 *
 */
void applet_init(applet_t* applet, const applet_privileges_t* privileges,
                 applet_unload_cb_t unload_cb);

/**
 * @brief Runs the applet task first time.
 *
 * When calling this function, the applet task must be initialized
 * and not running. The function does not return until the applet
 * gives up control (by being rescheduled out or terminated).
 *
 * @param applet Pointer to the applet to run.
 */
void applet_run(applet_t* applet);

/**
 * @brief Releases all resources held by the applet
 * @param applet Pointer to the applet to stop.
 */
void applet_unload(applet_t* applet);

/**
 * @brief Returns `true` if the applet task is alive.
 * @param applet Pointer to the applet to query.
 * @return true if the applet task is alive, false otherwise.
 */
bool applet_is_alive(applet_t* applet);

/**
 * @brief Returns the currently active applet.
 * @return Pointer to the currently active applet, or NULL if none.
 */
applet_t* applet_active(void);

#endif  // KERNEL
