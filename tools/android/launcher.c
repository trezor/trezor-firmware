// Run libmain.so from the same directory, as SDLActivity does in the APK.

#include <dlfcn.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
  char path[PATH_MAX];
  ssize_t len = readlink("/proc/self/exe", path, sizeof(path) - 1);
  if (len < 0) {
    perror("readlink");
    return 1;
  }
  path[len] = '\0';
  char *slash = strrchr(path, '/');
  if (slash == NULL ||
      snprintf(slash + 1, sizeof(path) - (slash + 1 - path), "libmain.so") >=
          (int)(sizeof(path) - (slash + 1 - path))) {
    fprintf(stderr, "launcher: path too long\n");
    return 1;
  }

  void *lib = dlopen(path, RTLD_NOW);
  if (lib == NULL) {
    fprintf(stderr, "launcher: %s\n", dlerror());
    return 1;
  }
  int (*sdl_main)(int, char **) = (int (*)(int, char **))dlsym(lib, "SDL_main");
  if (sdl_main == NULL) {
    fprintf(stderr, "launcher: %s\n", dlerror());
    return 1;
  }
  return sdl_main(argc, argv);
}
