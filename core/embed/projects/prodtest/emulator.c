#include <trezor_model.h>
#include <trezor_rtl.h>

#include <stdlib.h>
#include <unistd.h>

#include <SDL3/SDL.h>

#include <io/display.h>
#include <sys/flash.h>
#include <sys/flash_otp.h>

#ifdef LOCKABLE_BOOTLOADER
#include <sec/secret.h>
#endif

int prodtest_main(void);

void usage(void) {
  printf("Usage: ./build/prodtest/prodtest_emu [options]\n");
  printf(
      "To connect via terminal, install socat (i.e. 'sudo apt-get install "
      "socat' in Ubuntu)\n");
  printf(
      "Bind the UDP with 'socat -d -d  "
      "pty,link=/dev/ttyVCP0,mode=666,raw,echo=0   UDP:127.0.0.1:21327'\n");
  printf("Then you can connect with you terminal to /dev/ttyVCP0\n");
  printf("  -h  show this help\n");
}

static bool sdl_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_EVENT_QUIT:
      exit(3);
      return false;
    case SDL_EVENT_KEY_UP:
      if (event->key.repeat) {
        return false;
      }
      switch (event->key.key) {
        case SDLK_ESCAPE:
          exit(3);
          return false;
        case SDLK_S:
          display_save("emu");
          return false;
      }
      break;
  }
  return true;
}

int main(int argc, char **argv) {
  SDL_SetEventFilter(sdl_event_filter, NULL);

  display_init(DISPLAY_RESET_CONTENT);
  flash_init();
  flash_otp_init();

#ifdef LOCKABLE_BOOTLOADER
  secret_lock_bootloader();
#endif

  int opt;
  while ((opt = getopt(argc, argv, "h")) != -1) {
    switch (opt) {
      default:
        usage();
        exit(1);
    }
  }

  int exit_code = prodtest_main();

  char msg[64];
  snprintf(msg, sizeof(msg), "Exit code: %d", exit_code);

  error_shutdown_ex("PRODTEST ERROR", msg, "UNEXPECTED EXIT");
  return 0;
}
