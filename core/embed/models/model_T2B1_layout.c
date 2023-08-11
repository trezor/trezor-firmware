#include "flash.h"
#include "model.h"

const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT] = {
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 4,
                .num_sectors = 1,
            },
    },
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 16,
                .num_sectors = 1,
            },
    },
};

const flash_area_t BOARDLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 0,
            .num_sectors = 3,
        },
};

const flash_area_t SECRET_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 12,
            .num_sectors = 1,
        },
};

const flash_area_t TRANSLATIONS_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 13,
            .num_sectors = 2,
        },
};

const flash_area_t BOOTLOADER_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = 5,
            .num_sectors = 1,
        },
};

const flash_area_t FIRMWARE_AREA = {
    .num_subareas = 2,
    .subarea[0] =
        {
            .first_sector = 6,
            .num_sectors = 6,
        },
    .subarea[1] =
        {
            .first_sector = 17,
            .num_sectors = 7,
        },
};

const flash_area_t WIPE_AREA = {
    .num_subareas = 3,
    .subarea[0] =
        {
            .first_sector = 4,
            .num_sectors = 1,
        },
    .subarea[1] =
        {
            .first_sector = 6,
            .num_sectors = 6,
        },
    .subarea[2] =
        {
            .first_sector = 16,
            .num_sectors = 8,
        },
};
