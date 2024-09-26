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
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = FIRMWARE_SECTOR_START,
            .num_sectors = FIRMWARE_SECTOR_END - FIRMWARE_SECTOR_START + 1,
        },
};

const flash_area_t SECRET_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = SECRET_SECTOR_START,
            .num_sectors = SECRET_SECTOR_END - SECRET_SECTOR_START + 1,
        },
};

const flash_area_t BHK_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = BHK_SECTOR_START,
            .num_sectors = BHK_SECTOR_END - BHK_SECTOR_START + 1,
        },
};

const flash_area_t ASSETS_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = ASSETS_SECTOR_START,
            .num_sectors = ASSETS_SECTOR_END - ASSETS_SECTOR_START + 1,
        },
};

const flash_area_t UNUSED_AREA = {
    .num_subareas = 0,
};
