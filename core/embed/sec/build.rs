use xbuild::{Result, build_mods};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sys")?;

        build_mods!(lib;
            backup_ram if cfg!(feature = "backup_ram"),
            board_capabilities,
            consumption_mask if cfg!(feature = "consumption_mask"),
            fwutils,
            hash_processor if cfg!(feature = "hash_processor"),
            hw_revision if cfg!(feature = "hw_revision"),
            monoctr,
            option_bytes,
            image,
            iwdg if cfg!(feature = "iwdg"),
            optiga if cfg!(feature = "optiga"),
            random_delays /*if cfg!(feature = "random_delays") TODO !@#*/,
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
        );

        if cfg!(not(feature = "emulator")) && cfg!(not(feature = "secure_mode")) {
            // Linking sec layer in non-secure mode
            lib.add_source("../sys/smcall/stm32/smcall_stubs.c");
        }

        Ok(())
    })
}
