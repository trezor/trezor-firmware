#include <trezor_types.h>

uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str,
                                const uint8_t* fingerprint,
                                bool should_keep_seed, bool is_newvendor,
                                bool is_newinstall, int version_cmp);
uint32_t screen_wipe_confirm(void);
void screen_install_progress(int16_t progress, bool initialize,
                             bool initial_setup);
void screen_wipe_progress(int16_t progress, bool initialize);
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str,
                      bool fw_ok);
uint32_t screen_menu(secbool firmware_present);
void screen_connect(bool initial_setup);
void screen_wipe_success(void);
void screen_wipe_fail(void);
uint32_t screen_install_success(uint8_t restart_seconds, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
void screen_welcome(void);
void screen_boot_stage_1(bool fading);
uint32_t screen_unlock_bootloader_confirm(void);
void screen_unlock_bootloader_success(void);
void bld_continue_label(uint16_t bg_color);
void screen_boot(bool warning, const char* vendor_str, size_t vendor_str_len,
                 uint32_t version, const void* vendor_img,
                 size_t vendor_img_len, int wait);
