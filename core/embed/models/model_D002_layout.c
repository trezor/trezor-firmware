#include "flash.h"
#include "model.h"

const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT] = {
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 256 + 240,
                .num_sectors = 8,
            },
    },
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 256 + 248,
                .num_sectors = 8,
            },
    },
};

const flash_area_t BOARDLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0,
            .num_sectors = 16,
        },
};

const flash_area_t BOOTLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0x08,
            .num_sectors = 16,
        },
};

const flash_area_t FIRMWARE_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0x18,
            .num_sectors = 472,
        },
};

const flash_area_t WIPE_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0x18,
            .num_sectors = 488,
        },
};
