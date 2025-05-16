#include <trezor_model.h>
#include <trezor_rtl.h>

#include <unistd.h>

#include <SDL.h>

#include <io/display.h>
#include <util/flash.h>
#include <util/flash_otp.h>

#include <stdlib.h>

int prodtest_main(void);

void usage(void) {
  printf("Usage: ./build/prodtest/prodtest_emu [options]\n");
  printf("  -h  show this help\n");
}

static int sdl_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_QUIT:
      exit(3);
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          exit(3);
          return 0;
        case SDLK_p:
          display_save("emu");
          return 0;
      }
      break;
  }
  return 1;
}

int main(int argc, char **argv) {
  SDL_SetEventFilter(sdl_event_filter, NULL);

  display_init(DISPLAY_RESET_CONTENT);
  flash_init();
  flash_otp_init();

  int exit_code = prodtest_main();

  char msg[64];
  snprintf(msg, sizeof(msg), "Exit code: %d", exit_code);

  error_shutdown_ex("PRODTEST ERROR", msg, "UNEXPECTED EXIT");
  return 0;
}
