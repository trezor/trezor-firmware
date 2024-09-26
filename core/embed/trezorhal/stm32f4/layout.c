#include "flash.h"
#include "model.h"

const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT] = {
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = STORAGE_1_SECTOR_START,
                .num_sectors =
                    STORAGE_1_SECTOR_END - STORAGE_1_SECTOR_START + 1,
            },
    },
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = STORAGE_2_SECTOR_START,
                .num_sectors =
                    STORAGE_2_SECTOR_END - STORAGE_2_SECTOR_START + 1,
            },
    },
};

const flash_area_t BOARDLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = BOARDLOADER_SECTOR_START,
            .num_sectors =
                BOARDLOADER_SECTOR_END - BOARDLOADER_SECTOR_START + 1,
        },
};

const flash_area_t BOOTLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = BOOTLOADER_SECTOR_START,
            .num_sectors = BOOTLOADER_SECTOR_END - BOOTLOADER_SECTOR_START + 1,
        },
};

const flash_area_t FIRMWARE_AREA = {
    .num_subareas = 2,
    .subarea[0] =
        {
            .first_sector = FIRMWARE_P1_SECTOR_START,
            .num_sectors =
                FIRMWARE_P1_SECTOR_END - FIRMWARE_P1_SECTOR_START + 1,
        },
    .subarea[1] =
        {
            .first_sector = FIRMWARE_P2_SECTOR_START,
            .num_sectors =
                FIRMWARE_P2_SECTOR_END - FIRMWARE_P2_SECTOR_START + 1,
        },
};

#ifdef SECRET_SECTOR_START
const flash_area_t SECRET_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = SECRET_SECTOR_START,
            .num_sectors = SECRET_SECTOR_END - SECRET_SECTOR_START + 1,
        },
};
#else
const flash_area_t SECRET_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0,
            .num_sectors = 0,

        },
};
#endif

const flash_area_t ASSETS_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = ASSETS_SECTOR_START,
            .num_sectors = ASSETS_SECTOR_END - ASSETS_SECTOR_START + 1,
        },
};

const flash_area_t UNUSED_AREA = {
    .num_subareas = 2,
    .subarea[0] =
        {
            .first_sector = UNUSED_1_SECTOR_START,
            .num_sectors = UNUSED_1_SECTOR_END - UNUSED_1_SECTOR_START + 1,
        },
    .subarea[1] =
        {
            .first_sector = UNUSED_2_SECTOR_START,
            .num_sectors = UNUSED_2_SECTOR_END - UNUSED_2_SECTOR_START + 1,
        },
};
