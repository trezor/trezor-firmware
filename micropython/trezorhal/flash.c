#include STM32_HAL_H

int flash_init(void) {
    // Enable the flash IRQ, which is used to also call our storage IRQ handler
    // It needs to go at a higher priority than all those components that rely on
    // the flash storage (eg higher than USB MSC).
    HAL_NVIC_SetPriority(FLASH_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(FLASH_IRQn);

    return 0;
}

void FLASH_IRQHandler(void) {
    // This calls the real flash IRQ handler, if needed
    /*
    uint32_t flash_cr = FLASH->CR;
    if ((flash_cr & FLASH_IT_EOP) || (flash_cr & FLASH_IT_ERR)) {
        HAL_FLASH_IRQHandler();
    }
    */
    // This call the storage IRQ handler, to check if the flash cache needs flushing
    // storage_irq_handler();
}

#define WANTED_WRP (OB_WRP_SECTOR_0 | OB_WRP_SECTOR_1)
#define WANTED_RDP (OB_RDP_LEVEL_2)
#define WANTED_BOR (OB_BOR_LEVEL3)

void flash_set_option_bytes(void)
{
    FLASH_OBProgramInitTypeDef opts;

    HAL_FLASHEx_OBGetConfig(&opts);

    opts.OptionType = 0;

    if (opts.WRPSector != WANTED_WRP) {
        opts.OptionType = OPTIONBYTE_WRP;
        opts.WRPState = OB_WRPSTATE_ENABLE;
        opts.WRPSector = WANTED_WRP;
        opts.Banks = FLASH_BANK_1;
    }

    if (opts.RDPLevel != WANTED_RDP) {
        opts.OptionType = OPTIONBYTE_RDP;
        opts.RDPLevel = WANTED_RDP;
    }

    if (opts.BORLevel != WANTED_BOR) {
        opts.OptionType = OPTIONBYTE_BOR;
        opts.BORLevel = WANTED_BOR;
    }

    if (opts.OptionType != 0) {
        HAL_FLASHEx_OBProgram(&opts);
    }
}
