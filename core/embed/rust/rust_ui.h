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
                      uint8_t vendor_str_len, const char* version_str,
                      bool fw_ok);
uint32_t screen_menu(secbool firmware_present);
void screen_connect(bool initial_setup);
void screen_fatal_error_rust(const char* title, const char* msg,
                             const char* footer);
void screen_wipe_success(void);
void screen_wipe_fail(void);
uint32_t screen_install_success(uint8_t restart_seconds, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
void screen_welcome(void);
void screen_boot_empty(bool fading);
void screen_boot_full(void);
uint32_t screen_unlock_bootloader_confirm(void);
void screen_unlock_bootloader_success(void);
void display_image(int16_t x, int16_t y, const uint8_t* data, uint32_t datalen);
void display_icon(int16_t x, int16_t y, const uint8_t* data, uint32_t datalen,
                  uint16_t fg_color, uint16_t bg_color);
void bld_continue_label(uint16_t bg_color);
