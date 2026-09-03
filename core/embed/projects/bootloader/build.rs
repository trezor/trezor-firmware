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

        // Firmware presence/verification + firmware-update flow: the legacy
        // vendor/image-header path (fw_check.c + wf_firmware_update.c) or the
        // Merkle-tree path (fw_check_pq.c + wf_firmware_update_pq.c).
        // Exactly one; both provide `workflow_firmware_update`.
        if cfg!(feature = "pq_secure_boot") {
            lib.add_define("PQ_SECURE_BOOT", Some("1"));
            lib.add_source("fw_check_pq.c");
            lib.add_source("workflow/wf_firmware_update_pq.c");

            // Boot-warning logo for an unofficial (custom) firmware. The
            // Merkle-tree layout has no vendor header, so a logo has nowhere to
            // travel in: variants are founder-defined, not third-party, and the
            // only variant that ever draws this screen is the unofficial one
            // (fw_check_pq.c clears the warning for anything positively
            // official). So the bootloader owns the asset outright.
            //
            // Taken from the model's OWN vendorheader directory, which already
            // ships it sized and formatted for that model's UI -- 120x120 TOIF
            // on bolt/delizia/eckhart, 24x24 TOIG on caesar. That is what makes
            // this differentiate correctly the moment a second UI gets
            // pq_secure_boot: nothing here has to know about layouts.
            //
            // Section named `rodata_*` so the linker's existing `*(.rodata*)`
            // rule places it in FLASH: embed_binary renames `.data` to
            // `.<section>`, and a bespoke name would need a rule added to every
            // bootloader linker script.
            let model_id = xbuild::current_model_id()?;
            lib.embed_binary(
                format!("../../models/{model_id}/vendorheader/vendor_unsafe.toif"),
                "rodata_vendor_unsafe",
            )?;
            // nRF (BLE co-processor) OTA rides FirmwareBegin and needs the SMP
            // serial-recovery push (USE_SMP). nrf_staging.c persists the staged
            // image + descriptor across the reboot for the deferred phase-2 push.
            if cfg!(feature = "smp") {
                lib.add_source("workflow/wf_nrf_ota.c");
                lib.add_source("nrf_staging.c");
            }
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
