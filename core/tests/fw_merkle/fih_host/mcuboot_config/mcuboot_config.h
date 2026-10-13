/*
 * Minimal mcuboot_config for the host founder-verification harnesses.
 * Profile MEDIUM matches the device (trezor-ble/sysbuild/mcuboot.conf), so the
 * host gets the same FIH macro expansions (double vars, global fail, CFI).
 */
#ifndef H_MCUBOOT_CONFIG_HOST_
#define H_MCUBOOT_CONFIG_HOST_

#define MCUBOOT_FIH_PROFILE_MEDIUM 1

#endif
