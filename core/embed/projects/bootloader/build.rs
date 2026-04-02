use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("bootloader", |lib| {
        lib.import_lib("io")?;

        lib.add_includes([".", "protob"]);

        lib.add_include("../../rust"); // Cyclic dependency

        if cfg!(feature = "emulator") {
            lib.add_source("emulator.c");
            lib.add_source("../unix/profile.c"); // HACK!@#
        }

        lib.add_defines([
            ("PB_FIELD_16BIT", Some("1")),
            ("PB_ENCODE_ARRAYS_UNPACKED", Some("1")),
            ("PB_VALIDATE_UTF8", Some("1")),
        ]);

        lib.add_sources([
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

        if cfg!(not(feature = "emulator")) {
            if cfg!(feature = "boot_ucb") {
                lib.add_source("header_pq.c");
            } else {
                lib.add_source("header.S");
            }
        }

        if cfg!(feature = "lockable_bootloader") {
            lib.add_source("workflow/wf_unlock_bootloader.c");
        }

        if cfg!(feature = "disable_animation") {
            lib.add_define("DISABLE_ANIMATION", Some("1"));
        }

        if cfg!(feature = "debuglink") {
            lib.add_sources([
                "workflow/debuglink.c",
                "wire/debug_iface_usb.c",
                "protob/protob_debug.c",
                "protob/pb/messages-debug.pb.c",
            ]);
        }

        // nanopb library
        lib.add_include("../../../vendor/nanopb");
        lib.add_sources_from_folder(
            "../../../vendor/nanopb/",
            ["pb_common.c", "pb_decode.c", "pb_encode.c"],
        );

        Ok(())
    })
}
