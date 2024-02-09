#include "sdcard_emu_mock.h"
#include <stdio.h>
#include <stdlib.h>
#include "profile.h"
#include "sdcard.h"

// By default, Emulator starts without mocked SD card, i.e. initially
// sdcard.is_present() == False
SDCardMock sd_mock = {
    .inserted = secfalse,
    .powered = secfalse,
    .filename = NULL,
    .buffer = NULL,
    .serial_number = 0,
    .capacity_bytes = 0,
    .blocks = 0 / SDCARD_BLOCK_SIZE,
    .manuf_ID = 0,
};

void set_sd_mock_filename(int serial_number) {
  if (sd_mock.serial_number == serial_number) {
    // serial_number determines the filename, so assuming the PROFILE_DIR
    // doesn't change during a lifetime of the emulator, we can skip the rename
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
  if (sd_mock.filename != NULL) {
    free(sd_mock.filename);
    sd_mock.filename = NULL;
  }

  sd_mock.filename = new_filename;
}
