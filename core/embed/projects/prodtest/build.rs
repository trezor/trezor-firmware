use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("prodtest", |lib| {
        lib.import_lib("io")?;

        lib.add_includes(["."]);

        lib.add_include("../../rust"); // Cyclic dependency

        lib.add_sources(["main.c", "commands.c"]);

        if cfg!(feature = "emulator") {
            lib.add_source("emulator.c");
            lib.add_source("../unix/profile.c"); // HACK!@#
        } else {
            lib.add_source("header.S");
        }

        lib.add_sources_from_folder(
            "cmd",
            [
                "common.c",
                "prodtest_boardloader.c",
                "prodtest_ble.c",
                "prodtest_bootloader.c",
                "prodtest_button.c",
                "prodtest_crc.c",
                "prodtest_display.c",
                "prodtest_prodtest.c",
                "prodtest_backup_ram.c",
                "prodtest_get_cpuid.c",
                "prodtest_haptic.c",
                "prodtest_help.c",
                "prodtest_hw_revision.c",
                "prodtest_nfc.c",
                "prodtest_rtc.c",
                "prodtest_nrf.c",
                "prodtest_manufacturing_lock.c",
                "prodtest_optiga.c",
                "prodtest_otp_batch.c",
                "prodtest_otp_variant.c",
                "prodtest_ping.c",
                "prodtest_power_manager.c",
                "prodtest_reboot.c",
                "prodtest_rgbled.c",
                "prodtest_sdcard.c",
                "prodtest_secrets.c",
                "prodtest_tamper.c",
                "prodtest_sbu.c",
                "prodtest_secure_channel.c",
                "prodtest_telemetry.c",
                "prodtest_touch.c",
                "prodtest_tropic.c",
                "prodtest_unit_test.c",
                "prodtest_wpc.c",
                "secure_channel.c",
            ],
        );

        if cfg!(not(feature = "emulator")) {
            lib.embed_binary(
                xbuild::vendor_header_path("../../models", "prodtest")?,
                "vendorheader",
            )?;
        }

        Ok(())
    })
}
