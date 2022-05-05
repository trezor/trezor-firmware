#ifndef _SCREENS_RUST_H
#define _SCREENS_RUST_H

uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str, bool downgrade,
                                bool vendor);
uint32_t screen_wipe_confirm(void);
uint32_t screen_progress(const char* text, uint16_t progress, bool initialize);
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str);
uint32_t screen_menu(const char* bld_version_str);
uint32_t screen_connect(void);
uint32_t screen_fwinfo(const char* fingerprint);

#endif  //_SCREENS_RUST_H
