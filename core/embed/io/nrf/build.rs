use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("nrf/inc");

    lib.add_define("USE_NRF", Some("1"));

    // TODO: remove this hack when nrf related code in trezor_lib is
    // moved to this crate
    lib.add_private_include("../rust");

    if cfg!(feature = "emulator") {
        lib.add_sources(["nrf/unix/nrf.c"]);
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources([
            "nrf/stm32u5/nrf.c",
            "nrf/stm32u5/nrf_spi.c",
            "nrf/stm32u5/nrf_update.c",
            "nrf/crc8.c",
        ]);

        if cfg!(feature = "smp") {
            lib.add_define("USE_SMP", Some("1"));

            lib.add_sources(["nrf/stm32u5/nrf_uart.c", "nrf/stm32u5/nrf_test.c"]);
        }

        if cfg!(feature = "nrf_auth") {
            lib.add_define("USE_NRF_AUTH", Some("1"));
        }
    } else {
        bail_unsupported!();
    }

    Ok(())
}
