#include <stdbool.h>

#include "common.h"

uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str,
                                const uint8_t* fingerprint,
                                bool should_keep_seed, bool is_newvendor,
                                int version_cmp);
uint32_t screen_wipe_confirm(void);
void screen_install_progress(int16_t progress, bool initialize,
                             bool initial_setup);
void screen_wipe_progress(int16_t progress, bool initialize);
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str);
uint32_t screen_menu(void);
void screen_connect(void);
void screen_fatal_error_rust(const char* title, const char* msg,
                             const char* footer);
void screen_wipe_success(void);
void screen_wipe_fail(void);
uint32_t screen_install_success(const char* reboot_msg, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
void screen_welcome_model(void);
void screen_welcome(void);
void screen_boot_empty(bool fading);
void display_image(int16_t x, int16_t y, const uint8_t* data, uint32_t datalen);
