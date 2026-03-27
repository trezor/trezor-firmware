use xbuild::{CLibrary, Result, bail_unsupported};

// Define sys/bsp module
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("bsp/inc");

    if cfg!(feature = "emulator") {
        add_emulator_bsp(lib)?;
    } else if cfg!(feature = "mcu_stm32u5") {
        add_stm32u5_bsp(lib)?;
    } else if cfg!(feature = "mcu_stm32f4") {
        add_stm32f4_bsp(lib)?;
    } else {
        bail_unsupported!();
    }

    Ok(())
}

fn add_stm32u5_bsp(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "mcu_stm32u5g") {
        lib.add_define("STM32U5G9xx", None);
    } else if cfg!(feature = "mcu_stm32u58") {
        lib.add_define("STM32U585xx", None);
    } else {
        bail_unsupported!();
    }

    lib.add_defines([
        ("STM32_HAL_H", Some("<stm32u5xx.h>")),
        ("USE_HAL_DRIVER", None),
    ]);

    lib.add_includes([
        "../../vendor/cmsis_5/CMSIS/Core/Include",
        "../../vendor/cmsis_device_u5/Include",
        "../../vendor/stm32u5xx_hal_driver/Inc",
        "bsp/stm32u5",
    ]);

    lib.add_sources_from_folder(
        "../../vendor/stm32u5xx_hal_driver/Src/",
        [
            "stm32u5xx_hal.c",
            "stm32u5xx_hal_cortex.c",
            "stm32u5xx_hal_cryp.c",
            "stm32u5xx_hal_dma2d.c",
            "stm32u5xx_hal_dma.c",
            "stm32u5xx_hal_dma_ex.c",
            "stm32u5xx_hal_dsi.c",
            "stm32u5xx_hal_exti.c",
            "stm32u5xx_hal_flash.c",
            "stm32u5xx_hal_flash_ex.c",
            "stm32u5xx_hal_gfxmmu.c",
            "stm32u5xx_hal_gpio.c",
            "stm32u5xx_hal_gtzc.c",
            "stm32u5xx_hal_hash.c",
            "stm32u5xx_hal_hash_ex.c",
            "stm32u5xx_hal_i2c.c",
            "stm32u5xx_hal_i2c_ex.c",
            "stm32u5xx_hal_icache.c",
            "stm32u5xx_hal_iwdg.c",
            "stm32u5xx_hal_lptim.c",
            "stm32u5xx_hal_ltdc.c",
            "stm32u5xx_hal_ltdc_ex.c",
            "stm32u5xx_hal_pcd.c",
            "stm32u5xx_hal_pcd_ex.c",
            "stm32u5xx_hal_pwr.c",
            "stm32u5xx_hal_pwr_ex.c",
            "stm32u5xx_hal_ramcfg.c",
            "stm32u5xx_hal_rtc.c",
            "stm32u5xx_hal_rtc_ex.c",
            "stm32u5xx_hal_sd.c",
            "stm32u5xx_hal_spi.c",
            "stm32u5xx_hal_sram.c",
            "stm32u5xx_hal_tim.c",
            "stm32u5xx_hal_tim_ex.c",
            "stm32u5xx_hal_uart.c",
            "stm32u5xx_hal_uart_ex.c",
            "stm32u5xx_ll_fmc.c",
            "stm32u5xx_ll_usb.c",
            "stm32u5xx_ll_sdmmc.c",
        ],
    );

    if cfg!(feature = "secure_mode") {
        lib.add_sources_from_folder(
            "../../vendor/stm32u5xx_hal_driver/Src/",
            ["stm32u5xx_hal_rcc.c", "stm32u5xx_hal_rcc_ex.c"],
        );
    }

    Ok(())
}

fn add_stm32f4_bsp(lib: &mut CLibrary) -> Result<()> {
    lib.add_defines([
        ("STM32F427xx", None),
        ("STM32_HAL_H", Some("<stm32f4xx.h>")),
        ("USE_HAL_DRIVER", None),
    ]);

    lib.add_includes([
        "../../vendor/micropython/lib/cmsis/inc",
        "../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc",
        "../../vendor/micropython/lib/stm32lib/CMSIS/STM32F4xx/Include",
        "bsp/stm32f4",
    ]);

    lib.add_sources_from_folder(
        "../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/",
        [
            "stm32f4xx_hal.c",
            "stm32f4xx_hal_cortex.c",
            "stm32f4xx_hal_dma.c",
            "stm32f4xx_hal_dma2d.c",
            "stm32f4xx_hal_flash.c",
            "stm32f4xx_hal_flash_ex.c",
            "stm32f4xx_hal_gpio.c",
            "stm32f4xx_hal_i2c.c",
            "stm32f4xx_hal_ltdc.c",
            "stm32f4xx_hal_pcd.c",
            "stm32f4xx_hal_pcd_ex.c",
            "stm32f4xx_hal_pwr.c",
            "stm32f4xx_hal_rcc.c",
            "stm32f4xx_hal_rcc_ex.c",
            "stm32f4xx_hal_sd.c",
            "stm32f4xx_hal_spi.c",
            "stm32f4xx_hal_sram.c",
            "stm32f4xx_hal_sdram.c",
            "stm32f4xx_hal_tim.c",
            "stm32f4xx_hal_tim_ex.c",
            "stm32f4xx_ll_fmc.c",
            "stm32f4xx_ll_sdmmc.c",
            "stm32f4xx_ll_usb.c",
        ],
    );

    Ok(())
}

fn add_emulator_bsp(lib: &mut xbuild::CLibrary) -> Result<()> {
    lib.import_external_lib("sdl2", true)?;
    lib.import_external_lib("SDL2_image", true)?;

    Ok(())
}
