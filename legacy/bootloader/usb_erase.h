static void erase_storage_code_progress(void) {
  flash_enter();
  // erase storage area
  for (int i = FLASH_STORAGE_SECTOR_FIRST; i <= FLASH_STORAGE_SECTOR_LAST;
       i++) {
    layoutProgress("WIPING ... Please wait",
                   1000 * (i - FLASH_STORAGE_SECTOR_FIRST) /
                       (FLASH_CODE_SECTOR_LAST - FLASH_STORAGE_SECTOR_FIRST));
    flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
  }
  // erase code area
  for (int i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
    layoutProgress("WIPING ... Please wait",
                   1000 * (i - FLASH_STORAGE_SECTOR_FIRST) /
                       (FLASH_CODE_SECTOR_LAST - FLASH_STORAGE_SECTOR_FIRST));
    flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
  }
  flash_exit();
}

static void erase_code_progress(void) {
  flash_enter();
  for (int i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
    layoutProgress("PREPARING ... Please wait",
                   1000 * (i - FLASH_CODE_SECTOR_FIRST) /
                       (FLASH_CODE_SECTOR_LAST - FLASH_CODE_SECTOR_FIRST));
    flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
  }
  layoutProgress("INSTALLING ... Please wait", 0);
  flash_exit();
}

static void erase_storage(void) {
  flash_enter();
  for (int i = FLASH_STORAGE_SECTOR_FIRST; i <= FLASH_STORAGE_SECTOR_LAST;
       i++) {
    flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
  }
  flash_exit();
}
