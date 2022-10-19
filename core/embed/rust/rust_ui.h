#include "common.h"

void loader_uncompress_r(int32_t y_offset, uint16_t fg_color, uint16_t bg_color,
                         uint16_t icon_color, int32_t progress,
                         int32_t indeterminate, const uint8_t* icon_data,
                         uint32_t icon_data_size);

uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str, bool downgrade,
                                bool vendor);
uint32_t screen_wipe_confirm(void);
uint32_t screen_install_progress(int16_t progress, bool initialize,
                                 bool initial_setup);
uint32_t screen_wipe_progress(int16_t progress, bool initialize);
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str);
uint32_t screen_menu(const char* bld_version_str);
uint32_t screen_connect(void);
uint32_t screen_fwinfo(const char* fingerprint);
uint32_t screen_fatal_error(const char* msg, const char* file);
uint32_t screen_error_shutdown(const char* label, const char* msg);
uint32_t screen_wipe_success(void);
uint32_t screen_wipe_fail(void);
uint32_t screen_install_success(const char* reboot_msg, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
uint32_t screen_welcome(void);
void screen_boot_empty(bool firmware_present);
