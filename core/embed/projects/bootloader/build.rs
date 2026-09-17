use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("bootloader", |lib| {
        lib.import_lib("io")?;

        lib.add_includes([".", "protob"]);

        lib.add_include("../../rust"); // Cyclic dependency

        if cfg!(feature = "emulator") {
            lib.add_source("emulator.c");
        }

        lib.add_defines([
            ("PB_FIELD_16BIT", Some("1")),
            ("PB_ENCODE_ARRAYS_UNPACKED", Some("1")),
            ("PB_VALIDATE_UTF8", Some("1")),
            // Drops nanopb's error message strings (~1 kB of flash). Nothing
            // in the bootloader reads `pb_(i|o)stream_t::errmsg`.
            ("PB_NO_ERRMSG", Some("1")),
        ]);

        lib.add_sources([
            "bootui.c",
            "main.c",
            "ui_helpers.c",
            "version_check.c",
            "workflow/wf_image_upload.c",
            "workflow/wf_ucb_stage.c",
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

        // Legacy or Merkle-tree firmware check + update flow; exactly one, both
        // provide `workflow_firmware_update`.
        if cfg!(feature = "pq_secure_boot") {
            lib.add_source("fw_check_pq.c");
            lib.add_source("workflow/wf_firmware_update_pq.c");

            // Boot-warning logo for unofficial firmware (the tree layout has no
            // vendor header to carry one), taken from the model's own
            // vendorheader directory so it is already sized for its UI. The
            // `rodata_*` section name lets the existing `*(.rodata*)` linker
            // rule place it in flash.
            let model_id = xbuild::current_model_id()?;
            lib.embed_binary(
                format!("../../models/{model_id}/vendorheader/vendor_unsafe.toif"),
                "rodata_vendor_unsafe",
            )?;
        } else {
            lib.add_source("fw_check.c");
            lib.add_source("workflow/wf_firmware_update.c");
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
        lib.add_sources_in_dir(
            "../../../vendor/nanopb/",
            ["pb_common.c", "pb_decode.c", "pb_encode.c"],
        );

        Ok(())
    })
}
