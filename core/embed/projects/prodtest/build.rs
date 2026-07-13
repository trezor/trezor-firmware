use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("prodtest", |lib| {
        lib.import_lib("io")?;

        lib.add_includes(["."]);

        lib.add_include("../../rust"); // Cyclic dependency

        lib.add_sources(["main.c", "commands.c"]);

        if cfg!(feature = "emulator") {
            lib.add_source("emulator.c");
        } else if cfg!(feature = "pq_secure_boot") {
            // Merkle-tree layout: prodtest is a single secure module and its own
            // variant. Emit its TRZM module header + the (single-entry) manifest,
            // and stamp the prodtest variant. No legacy vendor/image/secmon header.
            lib.add_define("PQ_SECURE_BOOT", Some("1"));
            lib.add_source("module_header.S");
            lib.add_source("manifest_header.S");
            lib.add_define("FW_VARIANT", Some("4")); // FW_VARIANT_PRODTEST
        } else {
            lib.add_source("header.S");

            if cfg!(feature = "secmon_header") {
                lib.add_source("secmon_header.S");
            }
        }

        lib.add_sources_in_dir(
            "cmd",
            [
                "common.c",
                "prodtest_boardloader.c",
                "prodtest_button.c",
                "prodtest_crc.c",
                "prodtest_display.c",
                "prodtest_prodtest.c",
                "prodtest_backup_ram.c",
                "prodtest_get_cpuid.c",
                "prodtest_haptic.c",
                "prodtest_help.c",
                "prodtest_hw_revision.c",
                "prodtest_manufacturing_lock.c",
                "prodtest_otp_batch.c",
                "prodtest_otp_variant.c",
                "prodtest_ping.c",
                "prodtest_reboot.c",
                "prodtest_rgbled.c",
                "prodtest_sdcard.c",
                "prodtest_tamper.c",
                "prodtest_sbu.c",
                "prodtest_secure_channel.c",
                "prodtest_syslog.c",
                "prodtest_telemetry.c",
                "prodtest_touch.c",
                "prodtest_tropic.c",
                "prodtest_unit_test.c",
                "secure_channel.c",
            ],
        );

        if cfg!(not(feature = "emulator")) {
            lib.add_sources_in_dir(
                "cmd",
                [
                    "prodtest_ble.c",
                    "prodtest_bootloader.c",
                    "prodtest_nfc.c",
                    "prodtest_rtc.c",
                    "prodtest_nrf.c",
                    "prodtest_optiga.c",
                    "prodtest_power_manager.c",
                    "prodtest_secrets.c",
                    "prodtest_wpc.c",
                ],
            );

            // The Merkle-tree layout has no legacy vendor header (the module
            // header + manifest replace it).
            if !cfg!(feature = "pq_secure_boot") {
                lib.embed_binary(
                    xbuild::vendor_header_path("../../models", "prodtest")?,
                    "vendorheader",
                )?;
            }
        }

        Ok(())
    })
}
