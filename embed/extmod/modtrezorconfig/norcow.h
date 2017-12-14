#ifndef __NORCOW_H__
#define __NORCOW_H__

#include <stdint.h>
#include "../../trezorhal/secbool.h"

/*
 * Storage parameters:
 */

#define NORCOW_SECTOR_COUNT  2
#define NORCOW_SECTOR_SIZE   (64*1024)

/*
 * Initialize storage
 */
void norcow_init(void);

/*
 * Wipe the storage
 */
void norcow_wipe(void);

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len);

/*
 * Sets the given key, returns status of the operation
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len);

/*
 * Update a word in flash in the given key at the given offset.
 * Note that you can only change bits from 1 to 0.
 */
secbool norcow_update(uint16_t key, uint16_t offset, uint32_t value);

#endif
