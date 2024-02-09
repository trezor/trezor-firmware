#ifndef __TREZOR_SDCARD_EMULATOR_MOCK_H__
#define __TREZOR_SDCARD_EMULATOR_MOCK_H__

#include <stdint.h>
#include "secbool.h"

#ifndef ONE_MEBIBYTE
#define ONE_MEBIBYTE (1024 * 1024)
#endif

typedef struct {
  secbool inserted;
  secbool powered;
  char *filename;
  uint8_t *buffer;
  uint32_t serial_number;
  uint32_t capacity_bytes;
  uint32_t blocks;
  uint8_t manuf_ID;
} SDCardMock;

extern SDCardMock sd_mock;

void set_sd_mock_filename(int serial_number);

#endif  // __TREZOR_SDCARD_EMULATOR_MOCK_H__
