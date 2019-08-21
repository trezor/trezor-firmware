/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __RECOVERY_H__
#define __RECOVERY_H__

#include <stdbool.h>
#include <stdint.h>

void recovery_init(uint32_t _word_count, bool passphrase_protection,
                   bool pin_protection, const char *language, const char *label,
                   bool _enforce_wordlist, uint32_t type, uint32_t u2f_counter,
                   bool _dry_run);
void recovery_word(const char *word);
void recovery_abort(void);
const char *recovery_get_fake_word(void);
uint32_t recovery_get_word_pos(void);

#endif
