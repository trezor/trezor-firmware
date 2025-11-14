#pragma once

#include <trezor_types.h>

bool smp_echo(const char* text, uint8_t text_len);

void smp_reset(void);

/// Get the nRF app version string.
///
/// @param version_buf Buffer to write the version string (null-terminated)
/// @param buf_len Size of the buffer
/// @return Number of bytes written (excluding null terminator), or 0 on error
size_t smp_image_version_get(char* version_buf, size_t buf_len);

void smp_process_rx_byte(uint8_t byte);

bool smp_upload_app_image(const uint8_t* data, size_t len,
                          const uint8_t* image_hash, size_t image_hash_len);
