#pragma once

#include <trezor_types.h>

bool smp_echo(const char* text, uint8_t text_len);

void smp_reset(void);

void smp_process_rx_byte(uint8_t byte);

bool smp_upload_app_image(const uint8_t* data, size_t len,
                          const uint8_t* image_hash, size_t image_hash_len);
