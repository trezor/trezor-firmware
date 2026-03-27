use xbuild::Result;

#[path = "backup_ram/build.rs"]
mod backup_ram;

#[path = "board_capabilities/build.rs"]
mod board_capabilities;

#[path = "consumption_mask/build.rs"]
mod consumption_mask;

#[path = "fwutils/build.rs"]
mod fwutils;

#[path = "image/build.rs"]
mod image;

#[path = "iwdg/build.rs"]
mod iwdg;

#[path = "hash_processor/build.rs"]
mod hash_processor;

#[path = "hw_revision/build.rs"]
mod hw_revision;

#[path = "monoctr/build.rs"]
mod monoctr;

#[path = "optiga/build.rs"]
mod optiga;

#[path = "option_bytes/build.rs"]
mod option_bytes;

#[path = "random_delays/build.rs"]
mod random_delays;

#[path = "rng/build.rs"]
mod rng;

#[path = "rsod/build.rs"]
mod rsod;

#[path = "secret/build.rs"]
mod secret;

#[path = "secret_keys/build.rs"]
mod secret_keys;

#[path = "secure_aes/build.rs"]
mod secure_aes;

#[path = "storage/build.rs"]
mod storage;

#[path = "suspend/build.rs"]
mod suspend;

#[path = "tamper/build.rs"]
mod tamper;

#[path = "telemetry/build.rs"]
mod telemetry;

#[path = "time_estimate/build.rs"]
mod time_estimate;

#[path = "tropic/build.rs"]
mod tropic;

#[path = "unit_properties/build.rs"]
mod unit_properties;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sys")?;

        board_capabilities::def_module(lib)?;

        if cfg!(feature = "consumption_mask") {
            consumption_mask::def_module(lib)?;
        }

        fwutils::def_module(lib)?;

        if cfg!(feature = "hash_processor") {
            hash_processor::def_module(lib)?;
        }

        if cfg!(feature = "hw_revision") {
            hw_revision::def_module(lib)?;
        }

        if cfg!(feature = "backup_ram") {
            backup_ram::def_module(lib)?;
        }

        monoctr::def_module(lib)?;

        option_bytes::def_module(lib)?;

        image::def_module(lib)?;

        if cfg!(feature = "iwdg") {
            iwdg::def_module(lib)?;
        }

        if cfg!(feature = "optiga") {
            optiga::def_module(lib)?;
        }

        //if cfg!(feature = "random_delays") { // TODO!@#
        random_delays::def_module(lib)?;
        //}

        rng::def_module(lib)?;

        rsod::def_module(lib)?;

        if cfg!(feature = "secret") {
            secret::def_module(lib)?;
        }

        secret_keys::def_module(lib)?;

        if cfg!(feature = "secure_aes") {
            secure_aes::def_module(lib)?;
        }

        if cfg!(feature = "storage") {
            storage::def_module(lib)?;
        }

        if cfg!(feature = "suspend") {
            suspend::def_module(lib)?;
        }

        if cfg!(feature = "tamper") {
            tamper::def_module(lib)?;
        }

        if cfg!(feature = "telemetry") {
            telemetry::def_module(lib)?;
        }

        if cfg!(feature = "time_estimate") {
            time_estimate::def_module(lib)?;
        }

        if cfg!(feature = "tropic") {
            tropic::def_module(lib)?;
        }

        unit_properties::def_module(lib)?;

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "secure_mode")) {
            // Linking sec layer in non-secure mode
            lib.add_source("../sys/smcall/stm32/smcall_stubs.c");
        }

        Ok(())
    })
}
