fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("io");

    lib.add_includes(&["."]);

    lib.add_include("../../rust"); // TODO!@# temporary hack

    lib.add_sources(&["main.c", "commands.c"]);

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("emulator.c");
        lib.add_source("../unix/profile.c"); // HACK!@#
    } else {
        lib.add_source("header.S");
    }

    /*if cfg!(feature = "secmon_layout???") { //TODO!@#
        //TODO!@#
        lib.add_source("secmon_header.S");
    }*/

    lib.add_sources_from_folder(
        "cmd",
        &[
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

    lib.build();

    cbuild::emit_linker_args("prodtest");

    //TODO!@# move to emit_linker_args
    println!("cargo:rustc-link-arg=-Wl,-Bstatic");
    println!("cargo:rustc-link-arg=-lio");
    println!("cargo:rustc-link-arg=-lsec");
    println!("cargo:rustc-link-arg=-lsys");
    println!("cargo:rustc-link-arg=-lrtl");
}
