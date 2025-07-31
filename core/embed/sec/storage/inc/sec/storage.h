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

#include <vendor/trezor-storage/storage.h>

/**
 * Initialize storage and optionally register a UI progress callback.
 *
 * If storage is already initialized, this call locks it, restoring the
 * post-initialization state, and replaces the existing callback.
 *
 * @param callback  Callback invoked during long-term operations (may be NULL).
 */
void storage_setup(PIN_UI_WAIT_CALLBACK callback);
