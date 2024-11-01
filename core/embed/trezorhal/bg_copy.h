
#ifndef TREZORHAL_BG_COPY_H
#define TREZORHAL_BG_COPY_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

/**
 * Callback function invoked from the IRQ context
 * when the transfer is complete
 */
typedef void (*bg_copy_callback_t)(void);

/**
 * Performs data copy from src to dst in the background. The destination is
 * constant, meaning the address is not incremented. Ensure the transfer
 * completion by calling bg_copy_wait
 *
 * @param src source data address
 * @param dst destination data address
 * @param size size of data to be transferred in bytes
 * @param callback optional callback to be called when the transfer is complete
 */
void bg_copy_start_const_out_8(const uint8_t *src, uint8_t *dst, size_t size,
                               bg_copy_callback_t callback);

/**
 * Waits for the data transfer completion
 */
void bg_copy_wait(void);

/**
 * Immediately aborts the data transfer
 *
 * @note The callback will not be called
 */

void bg_copy_abort(void);

#endif  // KERNEL_MODE

#endif
