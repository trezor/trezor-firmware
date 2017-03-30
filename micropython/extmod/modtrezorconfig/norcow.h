#ifndef __NORCOW_H__
#define __NORCOW_H__

#include <stdint.h>
#include <stdbool.h>

/*
 * Storage parameters:
 */

#define NORCOW_SECTOR_COUNT  2
#define NORCOW_SECTOR_SIZE   (16*1024)

/*
 * Initialize storage
 */
bool norcow_init(void);

/*
 * Wipe the storage
 */
bool norcow_wipe(void);

/*
 * Looks for the given key, returns status of the operation
 */
bool norcow_get(uint16_t key, const void **val, uint16_t *len);

/*
 * Sets the given key, returns status of the operation
 */
bool norcow_set(uint16_t key, const void *val, uint16_t len);

#endif
