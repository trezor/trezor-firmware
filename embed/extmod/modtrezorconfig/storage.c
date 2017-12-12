/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>

#include "common.h"
#include "norcow.h"
#include "../../trezorhal/flash.h"

// Norcow storage key of configured PIN.
#define PIN_KEY 0x0000

// Maximum PIN length.
#define PIN_MAXLEN 32

// Byte-length of flash section containing fail counters.
#define PIN_FAIL_KEY 0x0001
#define PIN_FAIL_SECTOR_SIZE 32

// Maximum number of failed unlock attempts.
#define PIN_MAX_TRIES 15

static secbool initialized = secfalse;
static secbool unlocked = secfalse;

void storage_init(void)
{
    initialized = secfalse;
    unlocked = secfalse;
    flash_init();
    norcow_init();
    initialized = sectrue;
}

static void pin_fails_reset(uint16_t ofs)
{
    norcow_update(PIN_FAIL_KEY, ofs, 0);
}

static secbool pin_fails_increase(const uint32_t *ptr, uint16_t ofs)
{
    uint32_t ctr = *ptr;
    ctr = ctr << 1;

    flash_unlock();
    if (sectrue != norcow_update(PIN_FAIL_KEY, ofs, ctr)) {
        flash_lock();
        return secfalse;
    }
    flash_lock();

    uint32_t check = *ptr;
    if (ctr != check) {
        return secfalse;
    }
    return sectrue;
}

static void pin_fails_check_max(uint32_t ctr)
{
    if (~ctr >= (1 << PIN_MAX_TRIES)) {
        norcow_wipe();
        ensure(secfalse, "pin_fails_check_max");
    }
}

static secbool const_cmp(const uint8_t *pub, size_t publen, const uint8_t *sec, size_t seclen)
{
    size_t diff = seclen ^ publen;
    for (size_t i = 0; i < publen; i++) {
        diff |= pub[i] ^ sec[i];
    }
    return sectrue * (0 == diff);
}

static secbool pin_cmp(const uint8_t *pin, size_t pinlen)
{
    const void *spin = NULL;
    uint16_t spinlen = 0;
    norcow_get(PIN_KEY, &spin, &spinlen);
    if (NULL != spin) {
        return const_cmp(pin, pinlen, spin, spinlen);
    } else {
        return sectrue * (0 == pinlen);
    }
}

static secbool pin_check(const uint8_t *pin, size_t len)
{
    uint32_t ofs = 0;
    uint32_t ctr;
    const void *vpinfail;
    const uint32_t *pinfail = NULL;
    uint16_t pinfaillen;

    // The PIN_FAIL_KEY points to an area of words, initialized to
    // 0xffffffff (meaning no pin failures).  The first non-zero word
    // in this area is the current pin failure counter.  If  PIN_FAIL_KEY
    // has no configuration or is empty, the pin failure counter is 0.
    // We rely on the fact that flash allows to clear bits and we clear one
    // bit to indicate pin failure.  On success, the word is set to 0,
    // indicating that the next word is the pin failure counter.

    // Find the current pin failure counter
    secbool found = secfalse;
    if (secfalse != norcow_get(PIN_FAIL_KEY, &vpinfail, &pinfaillen)) {
        pinfail = vpinfail;
        for (ofs = 0; ofs < pinfaillen / sizeof(uint32_t); ofs++) {
            if (pinfail[ofs]) {
                found = sectrue;
                break;
            }
        }
    }
    if (found == secfalse) {
        // No pin failure section, or all entries used -> create a new one.
        uint32_t pinarea[PIN_FAIL_SECTOR_SIZE];
        memset(pinarea, 0xff, sizeof(pinarea));
        if (sectrue != norcow_set(PIN_FAIL_KEY, pinarea, sizeof(pinarea))) {
            return secfalse;
        }
        if (sectrue != norcow_get(PIN_FAIL_KEY, &vpinfail, &pinfaillen)) {
            return secfalse;
        }
        pinfail = vpinfail;
        ofs = 0;
    }

    // Read current failure counter
    ctr = pinfail[ofs];
    pin_fails_check_max(ctr);

    // Sleep for ~ctr seconds before checking the PIN.
    for (uint32_t wait = ~ctr; wait > 0; wait--) {
        hal_delay(1000);
    }

    // First, we increase PIN fail counter in storage, even before checking the
    // PIN.  If the PIN is correct, we reset the counter afterwards.  If not, we
    // check if this is the last allowed attempt.
    if (sectrue != pin_fails_increase(pinfail + ofs, ofs * sizeof(uint32_t))) {
        return secfalse;
    }
    if (sectrue != pin_cmp(pin, len)) {
        pin_fails_check_max(ctr << 1);
        return secfalse;
    }
    // Finally set the counter to 0 to indicate success.
    pin_fails_reset(ofs * sizeof(uint32_t));

    return sectrue;
}

secbool storage_unlock(const uint8_t *pin, size_t len)
{
    unlocked = secfalse;
    if (sectrue == initialized && sectrue == pin_check(pin, len)) {
        unlocked = sectrue;
    }
    return unlocked;
}

secbool storage_get(uint16_t key, const void **val, uint16_t *len)
{
    if (sectrue != initialized || sectrue != unlocked || (key >> 8) == 0) {
        return secfalse;
    }
    return norcow_get(key, val, len);
}

secbool storage_set(uint16_t key, const void *val, uint16_t len)
{
    if (sectrue != initialized || sectrue != unlocked || (key >> 8) == 0) {
        return secfalse;
    }
    return norcow_set(key, val, len);
}

secbool storage_has_pin(void)
{
    if (sectrue != initialized) {
        return secfalse;
    }
    const void *spin = NULL;
    uint16_t spinlen = 0;
    norcow_get(PIN_KEY, &spin, &spinlen);
    return sectrue * (0 != spinlen);
}

secbool storage_change_pin(const uint8_t *pin, size_t len, const uint8_t *newpin, size_t newlen)
{
    if (sectrue != initialized || sectrue != unlocked || newlen > PIN_MAXLEN) {
        return secfalse;
    }
    if (sectrue != pin_check(pin, len)) {
        return secfalse;
    }
    return norcow_set(PIN_KEY, newpin, newlen);
}

void storage_wipe(void)
{
    norcow_wipe();
}
