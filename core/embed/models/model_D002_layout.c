#include "flash.h"
#include "model.h"

const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT] = {
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 0x18,
                .num_sectors = 8,
            },
    },
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 0x20,
                .num_sectors = 8,
            },
    },
};

const flash_area_t BOARDLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 2,
            .num_sectors = 6,
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
            .first_sector = 0x28,
            .num_sectors = 464,
        },
};

const flash_area_t SECRET_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0,
            .num_sectors = 2,
        },
};

const flash_area_t BHK_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 1,
            .num_sectors = 1,
        },
};

const flash_area_t TRANSLATIONS_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 504,
            .num_sectors = 8,
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

const flash_area_t ALL_WIPE_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0x08,
            .num_sectors = 504,
        },
};
