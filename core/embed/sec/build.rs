use xbuild::{Result, build_mods};

#[path = "backup_ram/build.rs"]
mod backup_ram;
#[path = "board_capabilities/build.rs"]
mod board_capabilities;
#[path = "consumption_mask/build.rs"]
mod consumption_mask;
#[path = "fwutils/build.rs"]
mod fwutils;
#[path = "hash_processor/build.rs"]
mod hash_processor;
#[path = "hw_revision/build.rs"]
mod hw_revision;
#[path = "image/build.rs"]
mod image;
#[path = "iwdg/build.rs"]
mod iwdg;
#[path = "mcu_attestation/build.rs"]
mod mcu_attestation;
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
#[path = "trustzone/build.rs"]
mod trustzone;
#[path = "unit_properties/build.rs"]
mod unit_properties;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sys")?;

        build_mods!(
            lib,
            [
                backup_ram if cfg!(feature = "backup_ram"),
                board_capabilities,
                consumption_mask if cfg!(feature = "consumption_mask"),
                fwutils,
                hash_processor if cfg!(feature = "hash_processor"),
                hw_revision if cfg!(feature = "hw_revision"),
                mcu_attestation if cfg!(feature = "mcu_attestation"),
                monoctr,
                option_bytes,
                image,
                iwdg if cfg!(feature = "iwdg"),
                optiga if cfg!(feature = "optiga"),
                random_delays,
                rng,
                rsod,
                secret if cfg!(feature = "secret"),
                secret_keys,
                secure_aes if cfg!(feature = "secure_aes"),
                storage if cfg!(feature = "storage"),
                suspend if cfg!(feature = "suspend"),
                tamper if cfg!(feature = "tamper"),
                telemetry if cfg!(feature = "telemetry"),
                time_estimate if cfg!(feature = "time_estimate"),
                tropic if cfg!(feature = "tropic"),
                trustzone if cfg!(feature = "trustzone"),
                unit_properties,
            ]
        );

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "secure_mode")) {
            // Linking sec layer in non-secure mode
            lib.add_source("../sys/smcall/stm32/smcall_stubs.c");
        }

        Ok(())
    })
}
