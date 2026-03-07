fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("io");

    lib.add_includes(&[".", "protob"]);

    lib.add_include("../../rust"); // TODO!@# temporary hack

    lib.add_source("../unix/profile.c"); // HACK!@#

    lib.add_sources(&[
        "bootui.c",
        "fw_check.c",
        "main.c",
        "ui_helpers.c",
        "version_check.c",
        "workflow/wf_firmware_update.c",
        "workflow/wf_wipe_device.c",
        "workflow/wf_get_features.c",
        "workflow/wf_initialize.c",
        "workflow/wf_ping.c",
        "workflow/wf_bootloader.c",
        "workflow/wf_empty_device.c",
        "workflow/wf_auto_update.c",
        "workflow/wf_host_control.c",
        "workflow/wf_ble_pairing_request.c",
        "wire/codec_v1.c",
        "wire/wire_iface_usb.c",
        "wire/wire_iface_ble.c",
        "protob/protob.c",
        "protob/pb/messages.pb.c",
    ]);

    if !cfg!(feature = "boot_ucb") && !cfg!(feature = "mcu_emulator") {
        lib.add_source("header.S");
    }

    if cfg!(feature = "lockable_bootloader") {
        lib.add_source("workflow/wf_unlock_bootloader.c");
    }

    if false {
        //TODO!@# use debuglink feature
        lib.add_sources(&[
            "workflow/debuglink.c",
            "wire/debug_iface_usb.c",
            "protob/protob_debug.c",
            "protob/pb/messages-debug.pb.c",
        ]);
    }

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("emulator.c");
    }

    // nanopb library
    lib.add_public_include("../../../vendor/nanopb");
    lib.add_sources_from_folder(
        "../../../vendor/nanopb/",
        &["pb_common.c", "pb_decode.c", "pb_encode.c"],
    );

    lib.build();

    cbuild::emit_linker_args("bootloader");

    //TODO!@# move to emit_linker_args
    println!("cargo:rustc-link-arg=-Wl,-Bstatic");
    println!("cargo:rustc-link-arg=-lio");
    println!("cargo:rustc-link-arg=-lsec");
    println!("cargo:rustc-link-arg=-lsys");
    println!("cargo:rustc-link-arg=-lrtl");
}
