#include "sdcard_emu_mock.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "profile.h"
#include "sdcard.h"

// default SD Card filename serves for unit testing logic which requires SD card
// tests with emulator should call debuglink.insert_sdcard(...)
#define SDCARD_FILENAME_DEFAULT PROFILE_DIR_DEFAULT "/trezor.sdcard_def"

// default SD card data
SDCardMock sdcard_mock = {
    .inserted = sectrue,
    .filename = SDCARD_FILENAME_DEFAULT,
    .buffer = NULL,
    .serial_number = 1,
    .capacity_bytes = 64 * ONE_MEBIBYTE,
    .blocks = (64 * ONE_MEBIBYTE) / SDCARD_BLOCK_SIZE,
    .manuf_ID = 1,
};

// "not inserted" SD card data
/* SDCardMock sdcard_mock = { */
/*     .inserted = secfalse, */
/*     .filename = NULL, */
/*     .buffer = NULL, */
/*     .serial_number = 0, */
/*     .capacity_bytes = 0, */
/*     .blocks = 0 / SDCARD_BLOCK_SIZE, */
/*     .manuf_ID = 0, */
/* }; */

void set_sdcard_mock_filename(SDCardMock *card, int serial_number) {
  if (card == NULL) {
    return;
  }

  const char *dir_path = profile_dir();
  if (dir_path == NULL) {
    return;
  }

  // Calculate the length needed for the new full path
  // "trezor.sdcardXX" is 15 characters, plus the directory path and null
  // terminator
  const int full_path_length =
      snprintf(NULL, 0, "%s/trezor.sdcard%02d", dir_path, serial_number) + 1;
  char *new_filename = (char *)malloc(full_path_length);

  if (new_filename == NULL) {
    // memory allocation failure
    return;
  }
  // Construct the full path with leading zero in the filename for numbers less
  // than 10
  snprintf(new_filename, full_path_length, "%s/trezor.sdcard%02d", dir_path,
           serial_number);

  // free the old filename
  if (card->filename != NULL &&
      strcmp(card->filename, SDCARD_FILENAME_DEFAULT) != 0) {
    free(card->filename);
    card->filename = NULL;
  }

  card->filename = new_filename;
}
