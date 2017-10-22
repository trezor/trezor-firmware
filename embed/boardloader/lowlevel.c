#include STM32_HAL_H

#include "lowlevel.h"

#define WANTED_WRP (OB_WRP_SECTOR_0 | OB_WRP_SECTOR_1 | OB_WRP_SECTOR_2)
#define WANTED_RDP (OB_RDP_LEVEL_2)
#define WANTED_BOR (OB_BOR_LEVEL3)

void flash_set_option_bytes(void)
{
    FLASH_OBProgramInitTypeDef opts;

    for(;;) {
        HAL_FLASHEx_OBGetConfig(&opts);

        opts.OptionType = 0;

        if (opts.WRPSector != WANTED_WRP) {
            opts.OptionType |= OPTIONBYTE_WRP;
            opts.WRPState = OB_WRPSTATE_ENABLE;
            opts.WRPSector = WANTED_WRP;
            opts.Banks = FLASH_BANK_1;
        }

        if (opts.RDPLevel != WANTED_RDP) {
            opts.OptionType |= OPTIONBYTE_RDP;
            opts.RDPLevel = WANTED_RDP;
        }

        if (opts.BORLevel != WANTED_BOR) {
            opts.OptionType |= OPTIONBYTE_BOR;
            opts.BORLevel = WANTED_BOR;
        }

        if (opts.OptionType == 0) {
            break; // protections are configured
        }

        // attempt to lock down the boardloader sectors
        HAL_FLASHEx_OBProgram(&opts);
    }
}

bool flash_check_option_bytes(void)
{
    return
        ((FLASH->OPTCR & FLASH_OPTCR_nWRP) == (FLASH_OPTCR_nWRP_0 | FLASH_OPTCR_nWRP_1 | FLASH_OPTCR_nWRP_2)) &&
        ((FLASH->OPTCR & FLASH_OPTCR_RDP) == FLASH_OPTCR_RDP_2) &&
        ((FLASH->OPTCR & FLASH_OPTCR_BOR_LEV) == (FLASH_OPTCR_BOR_LEV_0 | FLASH_OPTCR_BOR_LEV_1));
}

void periph_init(void)
{
    // STM32F4xx HAL library initialization:
    //  - configure the Flash prefetch, instruction and data caches
    //  - configure the Systick to generate an interrupt each 1 msec
    //  - set NVIC Group Priority to 4
    //  - global MSP (MCU Support Package) initialization
    HAL_Init();

    // Enable GPIO clocks
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // enable the PVD (programmable voltage detector).
    // select the "2.7V" threshold (level 5). the typical electrical
    // characteristic values are similar to BOR level 3.
    // this detector will be active regardless of the
    // flash option byte BOR setting.
    __HAL_RCC_PWR_CLK_ENABLE();
    PWR_PVDTypeDef pvd_config;
    pvd_config.PVDLevel = PWR_PVDLEVEL_5;
    pvd_config.Mode = PWR_PVD_MODE_IT_RISING_FALLING;
    HAL_PWR_ConfigPVD(&pvd_config);
    HAL_PWR_EnablePVD();
    NVIC_EnableIRQ(PVD_IRQn);

    // Clear the reset flags
    RCC->CSR |= RCC_CSR_RMVF;
}
