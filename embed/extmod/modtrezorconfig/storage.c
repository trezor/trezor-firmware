/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>

#include "norcow.h"
#include "../../trezorhal/flash.h"

// Byte-length of flash sector containing fail counters.
#define PIN_AREA_LEN 0x4000

// Maximum number of failed unlock attempts.
#define PIN_MAX_TRIES 15

// Norcow storage key of configured PIN.
#define PIN_KEY 0x0000

static bool initialized = false;
static bool unlocked = false;

bool storage_init(void)
{
    if (!norcow_init()) {
        return false;
    }
    initialized = true;
    unlocked = false;
    return true;
}

static void pin_fails_reset(uint32_t ofs)
{
    if (ofs + sizeof(uint32_t) >= PIN_AREA_LEN) {
        // ofs points to the last word of the PIN fails area.  Because there is
        // no space left, we recycle the sector (set all words to 0xffffffff).
        // On next unlock attempt, we start counting from the the first word.
        flash_erase_sectors((uint8_t[]) { FLASH_SECTOR_PIN_AREA }, 1, NULL);
    } else {
        // Mark this counter as exhausted.  On next unlock attempt, pinfails_get
        // seeks to the next word.
        flash_unlock();
        flash_write_word_rel(FLASH_SECTOR_PIN_AREA, ofs, 0);
        flash_lock();
    }
}

static bool pin_fails_increase(uint32_t ofs)
{
    uint32_t ctr = ~PIN_MAX_TRIES;
    if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, ofs, &ctr)) {
        return false;
    }
    ctr = ctr << 1;

    flash_unlock();
    if (!flash_write_word_rel(FLASH_SECTOR_PIN_AREA, ofs, ctr)) {
        flash_lock();
        return false;
    }
    flash_lock();

    uint32_t check = 0;
    if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, ofs, &check)) {
        return false;
    }
    return ctr == check;
}

static void pin_fails_check_max(uint32_t ctr)
{
    if (~ctr >= 1 << PIN_MAX_TRIES) {
        for (;;) {
            if (norcow_wipe()) {
                break;
            }
        }
        // shutdown();
    }
}

static bool pin_fails_read(uint32_t *ofs, uint32_t *ctr)
{
    if (!ofs || !ctr) {
        return false;
    }
    for (uint32_t o = 0; o < PIN_AREA_LEN; o += sizeof(uint32_t)) {
        uint32_t c = 0;
        if (!flash_read_word_rel(FLASH_SECTOR_PIN_AREA, o, &c)) {
            return false;
        }
        if (c != 0) {
            *ofs = o;
            *ctr = c;
            return true;
        }
    }
    return false;
}

static bool const_cmp(const uint8_t *pub, size_t publen, const uint8_t *sec, size_t seclen)
{
    size_t diff = seclen ^ publen;
    for (size_t i = 0; i < publen; i++) {
        diff |= pub[i] ^ sec[i];
    }
    return diff == 0;
}

static bool pin_check(const uint8_t *pin, size_t pinlen)
{
    const void *st_pin;
    uint16_t st_pinlen;
    if (!norcow_get(PIN_KEY, &st_pin, &st_pinlen)) {
        return false;
    }
    return const_cmp(pin, pinlen, st_pin, (size_t)st_pinlen);
}

bool storage_unlock(const uint8_t *pin, size_t len)
{
    if (!initialized) {
        return false;
    }

    uint32_t ofs;
    uint32_t ctr;
    if (!pin_fails_read(&ofs, &ctr)) {
        return false;
    }
    pin_fails_check_max(ctr);

    // Sleep for ~ctr seconds before checking the PIN.
    for (uint32_t wait = ~ctr; wait > 0; wait--) {
        // hal_delay(1000);
    }

    // First, we increase PIN fail counter in storage, even before checking the
    // PIN.  If the PIN is correct, we reset the counter afterwards.  If not, we
    // check if this is the last allowed attempt.
    if (!pin_fails_increase(ofs)) {
        return false;
    }
    if (!pin_check(pin, len)) {
        pin_fails_check_max(ctr << 1);
        return false;
    }
    pin_fails_reset(ofs);
    return true;
}

bool storage_get(uint16_t key, const void **val, uint16_t *len)
{
    if (!initialized) {
        return false;
    }
    if (!unlocked) {
        // shutdown();
        return false;
    }
    if (key == PIN_KEY) {
        return false;
    }
    return norcow_get(key, val, len);
}

bool storage_set(uint16_t key, const void *val, uint16_t len)
{
    if (!initialized) {
        return false;
    }
    if (!unlocked) {
        // shutdown();
        return false;
    }
    if (key == PIN_KEY) {
        return false;
    }
    return norcow_set(key, val, len);
}

bool storage_wipe(void)
{
    return norcow_wipe();
}
