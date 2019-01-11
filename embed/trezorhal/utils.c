/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "utils.h"
#include STM32_HAL_H
#include "stm32f4xx_ll_utils.h"

/*
 * Returns the CPUID Base Register of the System Control Block.
 */
uint32_t utils_get_cpu_id()
{
    return SCB->CPUID;
}

/*
 * Returns the size of the device flash memory expressed in kilobytes, e.g. 0x040 corresponds to 64 kB.
 */
uint32_t utils_get_flash_size()
{
    return LL_GetFlashSize();
}

/*
 * Returns word 0 of the unique device identifier.
 */
uint32_t utils_get_uid_word0()
{
    return LL_GetUID_Word0();
}

/*
 * Returns word 1 of the unique device identifier.
 */
uint32_t utils_get_uid_word1()
{
    return LL_GetUID_Word1();
}

/*
 * Returns word 2 of the unique device identifier.
 */
uint32_t utils_get_uid_word2()
{
    return LL_GetUID_Word2();
}
