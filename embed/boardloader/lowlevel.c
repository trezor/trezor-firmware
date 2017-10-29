#include STM32_HAL_H

#include "lowlevel.h"

#define WANTED_WRP (OB_WRP_SECTOR_0 | OB_WRP_SECTOR_1 | OB_WRP_SECTOR_2)
#define WANTED_RDP (OB_RDP_LEVEL_2)

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

        if (opts.OptionType == 0) {
            break; // protections are configured
        }

        // attempt to lock down the boardloader sectors
        HAL_FLASH_Unlock();
        HAL_FLASH_OB_Unlock();
        HAL_FLASHEx_OBProgram(&opts);
        HAL_FLASH_OB_Launch();
        HAL_FLASH_OB_Lock();
        HAL_FLASH_Lock();
    }
}

secbool flash_check_option_bytes(void)
{
    if ((FLASH->OPTCR & FLASH_OPTCR_nWRP) != (FLASH_OPTCR_nWRP_0 | FLASH_OPTCR_nWRP_1 | FLASH_OPTCR_nWRP_2)) return secfalse;
    if ((FLASH->OPTCR & FLASH_OPTCR_RDP) != FLASH_OPTCR_RDP_2) return secfalse;
    return sectrue;
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
    // select the "2.6V" threshold (level 4).
    // this detector will be active regardless of the
    // flash option byte BOR setting.
    __HAL_RCC_PWR_CLK_ENABLE();
    PWR_PVDTypeDef pvd_config;
    pvd_config.PVDLevel = PWR_PVDLEVEL_4;
    pvd_config.Mode = PWR_PVD_MODE_IT_RISING_FALLING;
    HAL_PWR_ConfigPVD(&pvd_config);
    HAL_PWR_EnablePVD();
    NVIC_EnableIRQ(PVD_IRQn);
}

secbool reset_flags_init(void)
{
#if PRODUCTION
    // this is effective enough that it makes development painful, so only use it for production.
    // check the reset flags to assure that we arrive here due to a regular full power-on event,
    // and not as a result of a lesser reset.
    if ((RCC->CSR & (RCC_CSR_LPWRRSTF | RCC_CSR_WWDGRSTF | RCC_CSR_IWDGRSTF | RCC_CSR_SFTRSTF | RCC_CSR_PORRSTF | RCC_CSR_PINRSTF | RCC_CSR_BORRSTF)) != (RCC_CSR_PORRSTF | RCC_CSR_PINRSTF | RCC_CSR_BORRSTF)) {
        return secfalse;
    }
#endif

    RCC->CSR |= RCC_CSR_RMVF; // clear the reset flags

    return sectrue;
}
