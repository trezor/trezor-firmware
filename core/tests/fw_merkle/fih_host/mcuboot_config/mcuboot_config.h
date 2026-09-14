/*
 * Minimal mcuboot_config for the host founder-verification harnesses.
 *
 * bootutil/fault_injection_hardening.h includes this to pick its profile. MEDIUM
 * is deliberate, and matches the device (nordic/trezor/trezor-ble/sysbuild/
 * mcuboot.conf: CONFIG_BOOT_FIH_PROFILE_MEDIUM=y): it turns on
 * FIH_ENABLE_DOUBLE_VARS + FIH_ENABLE_GLOBAL_FAIL + FIH_ENABLE_CFI, so the host
 * exercises the SAME macro expansions the nRF gets -- masked success values, the
 * double-evaluating FIH_EQ/FIH_NOT_EQ, and CFI counter validation that catches a
 * FIH_CALL without a matching FIH_RET.
 *
 * Nothing else from mcuboot_config is needed: image_pq.c takes its SHA backend
 * from PQ_HOST_TEST, so the MCUboot crypto config is never consulted.
 */
#ifndef H_MCUBOOT_CONFIG_HOST_
#define H_MCUBOOT_CONFIG_HOST_

#define MCUBOOT_FIH_PROFILE_MEDIUM 1

#endif
