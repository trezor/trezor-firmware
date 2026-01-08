#pragma once

#include <trezor_types.h>

#include <sys/sysevent.h>

#include "rust_types.h"

// todo: use bindgen to bind return values to rust

// result screens
void screen_wipe_success(void);
void screen_wipe_fail(void);
uint32_t screen_install_success(uint8_t restart_seconds, bool initial_setup,
                                bool complete_draw);
uint32_t screen_install_fail(void);
void screen_unlock_bootloader_success(void);

// progress screens
void screen_install_progress(uint16_t progress, bool initialize,
                             bool initial_setup, bool wireless);
void screen_wipe_progress(uint16_t progress, bool initialize);

void screen_bootloader_entry_progress(uint16_t progress, bool initialize);

// simple screens with no interaction

void screen_boot_stage_1(bool fading);
void screen_boot_empty(void);
void screen_boot(bool warning, const char* vendor_str, size_t vendor_str_len,
                 uint32_t version, const void* vendor_img,
                 size_t vendor_img_len, int wait);

// confirm screens
typedef enum {
  CANCEL = 1,
  CONFIRM = 2,
} confirm_result_t;
uint32_t screen_install_confirm(const char* vendor_str, uint8_t vendor_str_len,
                                const char* version_str,
                                const uint8_t* fingerprint,
                                bool should_keep_seed, bool is_newvendor,
                                bool is_newinstall, int version_cmp);
uint32_t screen_wipe_confirm(void);
uint32_t screen_confirm_pairing(uint32_t code, bool initial_setup);
uint32_t screen_unlock_bootloader_confirm(void);

// screens with UI but no communication
typedef enum {
  INTRO_MENU = 1,
  INTRO_HOST = 2,
} intro_result_t;
uint32_t screen_intro(const char* bld_version_str, const char* vendor_str,
                      uint8_t vendor_str_len, const char* version_str,
                      bool fw_ok);

typedef enum {
  PAIRING_FINALIZATION_COMPLETED = 1,
  PAIRING_FINALIZATION_CANCEL = 2,
  PAIRING_FINALIZATION_FAILED = 3,
} pairing_mode_finalization_result_t;
uint32_t screen_pairing_mode_finalizing(bool initial_setup);

// screens with UI and communication interactions
typedef enum {
  MENU_EXIT = 0xAABBCCDD,
  MENU_REBOOT = 0x11223344,
  MENU_WIPE = 0x55667788,
  MENU_BLUETOOTH = 0x99AABBCC,
  MENU_POWER_OFF = 0x751A5BEF,
} menu_result_t;
uint32_t screen_menu(bool initial_setup, bool communication,
                     uint32_t* ui_result);

typedef enum {
  CONNECT_CANCEL = 1,
  CONNECT_PAIRING_MODE = 2,
  CONNECT_MENU = 3,
} connect_result_t;
uint32_t screen_connect(bool initial_setup, bool show_menu,
                        uint32_t* ui_result);

typedef enum {
  WELCOME_CANCEL = 1,
  WELCOME_PAIRING_MODE = 2,
  WELCOME_MENU = 3,
} welcome_result_t;

uint32_t screen_welcome(uint32_t* ui_result);

typedef enum {
  // 0 - 999999 - pairing code
  PAIRING_MODE_CANCEL = 1000000,
} pairing_mode_result_t;
uint32_t screen_pairing_mode(bool initial_setup, const char* name,
                             size_t name_len, uint32_t* ui_result);

typedef enum {
  // 0 - 999999 - pairing code
  WIRELESS_SETUP_CANCEL = 1000000,
} wireless_setup_result_t;
uint32_t screen_wireless_setup(const char* name, size_t name_len,
                               uint32_t* ui_result);
