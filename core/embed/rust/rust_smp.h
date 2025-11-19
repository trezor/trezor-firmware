#pragma once

#include <trezor_types.h>

/// Represents a parsed version string in the format:
/// "major.minor.patch[.build_num]" where build_num is optional and defaults to
/// 0 if absent.
typedef struct {
  uint8_t major;
  uint8_t minor;
  uint16_t revision;
  uint32_t build_num;  // optional part after, 0 if absent
} nrf_app_version_t;

bool smp_echo(const char* text, uint8_t text_len);

void smp_reset(void);

/// Fills nrf_app_version_t with the version of the active nRF app image.
/// Returns true on success, false on failure.
bool smp_image_version_get(nrf_app_version_t* out);

void smp_process_rx_byte(uint8_t byte);

bool smp_upload_app_image(const uint8_t* data, size_t len,
                          const uint8_t* image_hash, size_t image_hash_len);
