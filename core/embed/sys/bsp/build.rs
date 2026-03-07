// Define sys/bsp module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("bsp/inc");

    if cfg!(feature = "mcu_stm32u5") {
        add_stm32u5_bsp(lib);
    } else if cfg!(feature = "mcu_stm32f4") {
        add_stm32f4_bsp(lib);
    } else if cfg!(feature = "mcu_emulator") {
        add_emulator_bsp(lib);
    } else {
        unimplemented!();
    }
}

fn add_stm32u5_bsp(lib: &mut cbuild::CLibrary) {
    if cfg!(feature = "mcu_stm32u5g") {
        lib.add_public_define("STM32U5G9xx", None);
    } else if cfg!(feature = "mcu_stm32u58") {
        lib.add_public_define("STM32U585xx", None);
    } else {
        unimplemented!();
    }

    lib.add_public_defines(&[
        ("STM32_HAL_H", Some("<stm32u5xx.h>")),
        ("USE_HAL_DRIVER", None),
    ]);

    lib.add_public_includes(&[
        "../../vendor/cmsis_5/CMSIS/Core/Include",
        "../../vendor/cmsis_device_u5/Include",
        "../../vendor/stm32u5xx_hal_driver/Inc",
        "bsp/stm32u5",
    ]);

    lib.add_sources_from_folder(
        "../../vendor/stm32u5xx_hal_driver/Src/",
        &[
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
            "stm32u5xx_ll_fmc.c",
            "stm32u5xx_ll_usb.c",
            "stm32u5xx_ll_sdmmc.c",
        ],
    );

    if cfg!(feature = "secure_mode") {
        lib.add_sources_from_folder(
            "../../vendor/stm32u5xx_hal_driver/Src/",
            &["stm32u5xx_hal_rcc.c", "stm32u5xx_hal_rcc_ex.c"],
        );
    }
}

fn add_stm32f4_bsp(lib: &mut cbuild::CLibrary) {
    lib.add_public_defines(&[
        ("STM32F427xx", None),
        ("STM32_HAL_H", Some("<stm32f4xx.h>")),
        ("USE_HAL_DRIVER", None),
    ]);

    lib.add_public_includes(&[
        "../../vendor/micropython/lib/cmsis/inc",
        "../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc",
        "../../vendor/micropython/lib/stm32lib/CMSIS/STM32F4xx/Include",
        "bsp/stm32f4",
    ]);

    lib.add_sources_from_folder(
        "../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/",
        &[
            "stm32f4xx_hal.c",
            "stm32f4xx_hal_cortex.c",
            "stm32f4xx_hal_dma.c",
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
}

fn add_emulator_bsp(lib: &mut cbuild::CLibrary) {
    //HACK!@# ???
    lib.add_public_defines(&[("FLASH_BLOCK_WORDS", Some("4"))]);

    //TODO!@# use pkg-config to find SDL2
    lib.add_public_includes(&[
        "/nix/store/58cdrn1birpig59wqygva9cmsnxh7wwa-SDL2-2.26.4-dev/include/SDL2",
        "/nix/store/frhqd181g2g6l468g1gzx055dw0y560n-SDL2_image-2.6.3/include/SDL2",
    ]);
}
