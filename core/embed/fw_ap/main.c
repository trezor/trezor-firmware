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

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "embed/fw_cs/core_api.h"
#include <embed/fw_ss/secure_api.h>

int main(void) {  // UNPRIVILEGED APPLICATION

  char text[64];

  core_print("Unprivileged application is running...\n");

  // get secret from privileged-world
  snprintf(text, sizeof(text), "secret = %d\n", core_get_secret());
  core_print(text);

  // get secret from secure-world directly
  snprintf(text, sizeof(text), "secret = %d\n", secure_get_secret());
  core_print(text);


  while (1)
    ;

  return 0;
}
