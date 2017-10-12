#include <stdint.h>

#include "common.h"
#include "rng.h"

#include STM32_HAL_H

// reference RM0090 section 35.12.1 Figure 413
#define USB_OTG_HS_DATA_FIFO_RAM  (USB_OTG_HS_PERIPH_BASE + 0x20000U)
#define USB_OTG_HS_DATA_FIFO_SIZE (4096U)

void clear_otg_hs_memory(void)
{
    // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
    __HAL_RCC_USB_OTG_HS_CLK_ENABLE(); // enable USB_OTG_HS peripheral clock so that the peripheral memory is accessible
    const uint32_t unpredictable = rng_get();
    memset_reg((volatile void *) USB_OTG_HS_DATA_FIFO_RAM, (volatile void *) (USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE), unpredictable);
    memset_reg((volatile void *) USB_OTG_HS_DATA_FIFO_RAM, (volatile void *) (USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE), 0);
    __HAL_RCC_USB_OTG_HS_CLK_DISABLE(); // disable USB OTG_HS peripheral clock as the peripheral is not needed right now
}

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
