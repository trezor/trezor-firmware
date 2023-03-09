#include "common.h"

void loader_uncompress_r(int32_t y_offset, uint16_t fg_color, uint16_t bg_color,
                         uint16_t icon_color, int32_t progress,
                         int32_t indeterminate, const uint8_t* icon_data,
                         uint32_t icon_data_size);

uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str,
                                const uint8_t* fingerprint, bool downgrade,
                                bool vendor);
uint32_t screen_wipe_confirm(void);
void screen_install_progress(int16_t progress, bool initialize,
                             bool initial_setup);
void screen_wipe_progress(int16_t progress, bool initialize);
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str);
uint32_t screen_menu(const char* bld_version_str);
void screen_connect(void);
void screen_fatal_error_c(const char* msg, const char* file);
void screen_error_shutdown_c(const char* label, const char* msg);
void screen_wipe_success(void);
void screen_wipe_fail(void);
uint32_t screen_install_success(const char* reboot_msg, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
void screen_welcome(void);
void screen_boot_empty(bool firmware_present, bool fading);
