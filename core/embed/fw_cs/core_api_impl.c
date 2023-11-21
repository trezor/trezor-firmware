#include <core_api.h>

#include <display.h>

#include <embed/fw_ss/secure_api.h>

void core_print(char* text) { display_printf("%s", text); }

int core_get_secret(void) { return secure_get_secret(); }