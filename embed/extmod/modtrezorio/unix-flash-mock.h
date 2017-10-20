/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "../../trezorhal/flash.h"

void flash_set_option_bytes(void)
{
}

bool flash_unlock(void)
{
    return false;
}

bool flash_lock(void)
{
    return false;
}

bool flash_erase_sectors(const uint8_t *sectors, int len, void (*progress)(int pos, int len))
{
    return false;
}

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen)
{
    return false;
}

bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen)
{
    return false;
}

bool flash_otp_lock(uint8_t block)
{
    return false;
}

bool flash_otp_is_locked(uint8_t block)
{
    return false;
}
