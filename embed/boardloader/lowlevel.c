#include <stdint.h>

#include "common.h"
#include "rng.h"

#include STM32_HAL_H

#define WANTED_WRP (OB_WRP_SECTOR_0 | OB_WRP_SECTOR_1 | OB_WRP_SECTOR_2)
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
