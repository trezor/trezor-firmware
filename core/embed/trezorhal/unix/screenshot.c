#include "screenshot.h"
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "display_interface.h"

uint32_t REFRESH_INDEX = 0;
char SAVE_SCREEN_DIRECTORY[256] = {0};
bool SAVE_SCREEN = false;

void screenshot_init(void) {
  REFRESH_INDEX = 0;
  snprintf(SAVE_SCREEN_DIRECTORY, sizeof(SAVE_SCREEN_DIRECTORY), ".");
  SAVE_SCREEN = false;
}

bool screenshot(void) {
  if (SAVE_SCREEN_DIRECTORY[0] == 0) {
    screenshot_init();
  }

  if (SAVE_SCREEN) {
    // display_save(NULL);

    char prefix[512] = {0};
    snprintf(prefix, sizeof(prefix), "%s/refresh%02d-", SAVE_SCREEN_DIRECTORY,
             REFRESH_INDEX);
    display_save(prefix);
    return true;
  }
  return false;
}

void screenshot_clear(void) {
  SAVE_SCREEN = false;
  display_clear_save();
}

void screenshot_prepare(uint32_t refresh_index, const char *target_directory) {
  REFRESH_INDEX = refresh_index;
  strncpy(SAVE_SCREEN_DIRECTORY, target_directory,
          sizeof(SAVE_SCREEN_DIRECTORY));
  SAVE_SCREEN = true;
}
