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
secbool norcow_init(void);

/*
 * Wipe the storage
 */
secbool norcow_wipe(void);

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len);

/*
 * Sets the given key, returns status of the operation
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len);

#endif
