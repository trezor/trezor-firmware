
#ifndef TREZORHAL_BG_COPY_H
#define TREZORHAL_BG_COPY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/**
 * Wait for the data transfer completion
 */
void bg_copy_wait(void);

/**
 * Performs data copy from src to dst in the background. The destination is
 * constant, meaning the address is not incremented. Ensure the transfer
 * completion by calling bg_copy_wait
 *
 * @param src source data address
 * @param dst destination data address
 * @param size size of data to be transferred in bytes
 */
void bg_copy_start_const_out_8(const uint8_t *src, uint8_t *dst, size_t size);

#endif
